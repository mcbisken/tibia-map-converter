# cli.py — command-line front-end over convert.convert() / convert_to_canary()
# for batch use. The GUI (gui.py) remains the primary interface.
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="otbm-remapper",
        description="Remap a Tibia .otbm map's item ids onto another server's "
                    "item table (items.otb or Canary appearances.dat).")
    sub = ap.add_subparsers(dest="mode", required=True)

    classic = sub.add_parser("classic", help="items.otb -> items.otb (clientID-anchored)")
    classic.add_argument("--map", required=True, help="source .otbm map")
    classic.add_argument("--source-otb", required=True, help="source items.otb (old)")
    classic.add_argument("--target-otb", required=True, help="target items.otb (new)")
    classic.add_argument("--source-xml", help="source items.xml (names in report, custom xml)")
    classic.add_argument("--scripts", help="server scripts/data folder to scan for remapped ids")
    classic.add_argument("--out", required=True, help="output folder")

    canary = sub.add_parser("canary", help="source items.xml names -> Canary appearances.dat")
    canary.add_argument("--map", required=True, help="source .otbm map")
    canary.add_argument("--source-xml", required=True, help="source items.xml (old)")
    canary.add_argument("--appearances", required=True, help="target appearances.dat")
    canary.add_argument("--prefer-id", action="store_true",
                        help="same-era source: keep ids that already exist in the target")
    canary.add_argument("--scripts", help="server scripts/data folder to scan for remapped ids")
    canary.add_argument("--out", required=True, help="output folder")

    args = ap.parse_args(argv)
    try:
        if args.mode == "classic":
            s = convert.convert(args.map, args.source_otb, args.target_otb,
                                args.out, src_xml=args.source_xml,
                                scripts_dir=args.scripts)
            print(f"SUCCESS: matches={s.matches} customs={s.customs} "
                  f"ambiguous={s.ambiguous} unanchored={s.unanchored} "
                  f"mismatches={s.mismatches} container_risks={s.container_risks} "
                  f"changed={s.changed}")
        else:
            s = convert.convert_to_canary(args.map, args.source_xml,
                                          args.appearances, args.out,
                                          prefer_id=args.prefer_id,
                                          scripts_dir=args.scripts)
            print(f"SUCCESS: id_matched={s.id_matched} exact={s.exact} "
                  f"ambiguous={s.ambiguous} unmatched={s.unmatched} "
                  f"container_risks={s.container_risks} changed={s.changed}")
        if s.script_hits:
            print(f"NOTE: {s.script_hits} remapped ids referenced in scripts "
                  f"-> {s.out_script_report}")
        print(f"Review report: {s.out_report}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
