def get_response(msg, allowed=None):
    while True:
        res = input(f'{msg} (y/n{"/" if allowed else ""}{"/".join(allowed or [])})? ')
        if res == "y":
            return True
        if res == "n":
            return False
        if allowed and res in allowed:
            return res
        print("Invalid response, please try again")
