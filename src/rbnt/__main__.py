"""python -m rbnt <stage> [<stage> ...] | all | data | report"""

import importlib
import sys

from .stages import ORDER

GROUPS = {"all": ORDER, "data": ORDER[:6], "report": ORDER[6:]}

HELP = """Stages, in order:
  blocks    find the snapshot block for every moment of the edition
  crawl     read every block from genesis: addresses, watched events, quarter transactions
  traces    read every internal transfer from the explorer
  tags      read public name tags from the explorer
  holdings  read RBNT, WRBNT and staked RBNT of every address at each snapshot
  programs  read the verified program name of every contract holding RBNT
  tables    build the published tables and headline.json, with exact checks
  draw      draw the charts
  publish   write the web page, PDF, Word file, workbook and community files
  audit     re-read figures from the node and scan every published file
Groups: all, data (blocks to programs), report (tables to audit).
Options: audit --offline"""


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(HELP)
        return 0
    names = []
    for word in argv:
        if word.startswith("--"):
            continue
        names += GROUPS.get(word, [word])
    for name in names:
        if name not in ORDER:
            print(f"unknown stage: {name}\n\n{HELP}")
            return 2
    flags = [w for w in argv if w.startswith("--")]
    for name in names:
        print(f"== {name}", flush=True)
        code = importlib.import_module(f"rbnt.stages.{name}").run(flags)
        if code:
            return code
    return 0


sys.exit(main(sys.argv[1:]))
