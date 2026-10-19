"""Prepare the supplied revised collection without rewriting measured workbooks."""
import argparse
import hashlib
import shutil
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fatigue.imp.experimental_data import import_experimental_data_grouped_by_material
from fatigue.imp.schema import material_id


RETIRED_COLLECTION_IDS = {'Ti6Al4V_andrea_(AXIAL)', 'Ti6Al4V_andrea_(BENDING)'}


def install(archive, destination, *, apply=False):
    destination = Path(destination)
    with tempfile.TemporaryDirectory() as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                parts = Path(info.filename).parts
                if len(parts) == 2 and parts[0] == 'New_Exp_data' and parts[1].endswith('.xlsx'):
                    (extracted / parts[1]).write_bytes(z.read(info))
        data = import_experimental_data_grouped_by_material(extracted)
        if not data:
            raise ValueError('No revised workbooks found under New_Exp_data/')
        incoming = {material_id(p.stem): p for p in extracted.glob('*.xlsx')}
        previous = {material_id(p.stem): p for p in destination.glob('*.xlsx')}
        for material, block in data.items():
            issues = block['identity_issues'] + list(block['property_issues'].values())
            print(f'{material}: {len(block["cases"])} imported plain observations; issues {issues}')
        for material in sorted(previous.keys() - incoming.keys()):
            disposition = ('archived as a previous collection snapshot, without asserting alloy equivalence'
                           if material in RETIRED_COLLECTION_IDS else 'retained because no replacement was supplied')
            print(f'{material}: {disposition}')
        if not apply:
            print('Dry run completed. Use --apply to archive replaced files and install unchanged revised bytes.')
            return data
        # Verify every archive target before making any active-file change.
        archive_dir = destination / 'archive/pre-dataset-migration'
        for material, old in previous.items():
            if ((material not in incoming and material not in RETIRED_COLLECTION_IDS)
                    or (material in incoming and old.read_bytes() == incoming[material].read_bytes())):
                continue
            archived = archive_dir / old.name
            if archived.exists() and archived.read_bytes() != old.read_bytes():
                raise FileExistsError(f'Different historical workbook already exists: {archived}')
        archive_dir.mkdir(parents=True, exist_ok=True)
        destination.mkdir(parents=True, exist_ok=True)
        for material, old in previous.items():
            if (material in RETIRED_COLLECTION_IDS
                    or (material in incoming and old.read_bytes() != incoming[material].read_bytes())):
                shutil.copy2(old, archive_dir / old.name)
        for material, source in incoming.items():
            target = destination / source.name
            shutil.copy2(source, target)
            assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest()
            old = previous.get(material)
            if old and old.name != target.name:
                old.unlink()
        for material in RETIRED_COLLECTION_IDS & previous.keys():
            previous[material].unlink()
        print(f'Installed {len(incoming)} revised workbooks; no measured cells edited.')
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', help='Supplied exp_data.zip containing New_Exp_data/')
    parser.add_argument('--destination', default='Experimental_Data')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    install(args.archive, args.destination, apply=args.apply)


if __name__ == '__main__':
    main()
