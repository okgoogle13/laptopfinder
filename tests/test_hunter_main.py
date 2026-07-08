from laptopfinder.runners.ebay_hunter import build_parser

def test_no_enrich_flag_parsed():
    args = build_parser().parse_args(["--dry-run", "--no-enrich"])
    assert args.dry_run is True
    assert args.no_enrich is True

def test_no_enrich_flag_defaults_false():
    args = build_parser().parse_args([])
    assert args.no_enrich is False
