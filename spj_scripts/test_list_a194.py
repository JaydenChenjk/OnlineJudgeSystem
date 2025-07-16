import sys
def main():
    if len(sys.argv) != 3:
        print("Usage: spj.py std_output user_output", file=sys.stderr)
        sys.exit(3)
    std_path = sys.argv[1]
    user_path = sys.argv[2]
    try:
        with open(std_path, "r") as f_std, open(user_path, "r") as f_user:
            for std_line in f_std:
                user_line = f_user.readline()
                if user_line == "":
                    sys.exit(1)
                if std_line.rstrip() != user_line.rstrip():
                    sys.exit(1)
            if f_user.readline() != "":
                sys.exit(1)
    except Exception as e:
        print(f"Cannot open output files: {e}", file=sys.stderr)
        sys.exit(3)
    sys.exit(0)
if __name__ == "__main__":
    main()
