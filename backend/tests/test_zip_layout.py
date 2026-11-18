from datetime import datetime, timezone
from pathlib import PurePosixPath
from app.api.downloads import scoped_photo_paths


def test_pallet_order_folders_and_bangkok_date():
    manifest={'pallets':[{'id':'p1','number':1,'orders':['000123','ORDER-B']}]}
    photo={'id':'image-1','pallet_id':'p1','uploaded_at':datetime(2026,11,18,20,30,tzinfo=timezone.utc)}
    assert scoped_photo_paths(manifest,photo,1)==[
        'Pallet-001/000123/001-image-1_19112026.jpg',
        'Pallet-001/ORDER-B/001-image-1_19112026.jpg',
    ]


def test_unsafe_order_names_and_case_collisions_have_distinct_folders():
    orders=['../ORDER/A','..\\ORDER:A','CON','..','Order','ORDER','x'*100+'1','x'*100+'2']
    manifest={'pallets':[{'id':'p1','number':1,'orders':orders}]}
    photo={'id':'image','pallet_id':'p1','uploaded_at':datetime(2026,11,18,tzinfo=timezone.utc)}
    paths=scoped_photo_paths(manifest,photo,1)
    assert len({path.casefold() for path in paths})==len(orders)
    for path in paths:
        parts=PurePosixPath(path).parts
        assert len(parts)==3 and '..' not in parts and '\\' not in path
        assert not any(character in parts[1] for character in '/:*?"<>|')


def test_overview_missing_orders_and_legacy_duplicate_pallet_numbers():
    photo={'id':'image','pallet_id':None,'uploaded_at':datetime(2026,11,18,tzinfo=timezone.utc)}
    manifest={'pallets':[{'id':'p1','number':1,'orders':[]},{'id':'p2','number':1,'orders':[]}]}
    assert scoped_photo_paths(manifest,photo,1)==['Trip-overview/001-image_18112026.jpg']
    first=scoped_photo_paths(manifest,{**photo,'pallet_id':'p1'},1)[0]
    second=scoped_photo_paths(manifest,{**photo,'pallet_id':'p2'},1)[0]
    assert first.startswith('Pallet-001-p1/No-Order/') and first!=second
