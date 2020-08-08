from sys import stderr

def WARN(*argv):
    print("[WARN]", *argv, file=stderr)