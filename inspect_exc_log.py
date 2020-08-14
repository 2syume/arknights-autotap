from ArkDriver.cvUtils import bytes_to_pil
from argparse import ArgumentParser
import pickle
from pprint import pprint


parser = ArgumentParser()
parser.add_argument("-l", "--log_file", help="Log file to inspect", default="exc_full_log.data")
args = parser.parse_args()

with open(args.log_file, "rb") as f:
    logs = pickle.load(f)

total = len(logs)
for n, log in enumerate(logs):
    print(">>>> {}/{} <<<<".format(n+1, total))
    tb, last_log = log
    print("Traceback:")
    print("".join(tb))
    loaded_log = dict((k, bytes_to_pil(v) if k.endswith("_img") else v) for k,v in last_log.items())
    print("Last Log")
    pprint(loaded_log)
    for k in loaded_log:
        if k.endswith("_img"):
            loaded_log[k].show()
            input("Showing Image {} (Enter to continue)".format(k))

