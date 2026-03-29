import argparse
import jwt
import datetime

def generate_mock_token(agent_id, allowed):
    secret = "CERTIOR_FALLBACK_SECRET_CHANGE_ME_IN_PROD"
    payload = {
        "agent_id": agent_id,
        "permissions": allowed,
        # Milestone 9 Edge Case C: Expiration added strictly. 
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    }
    encoded_jwt = jwt.encode(payload, secret, algorithm="HS256")
    return encoded_jwt

def main():
    parser = argparse.ArgumentParser(description="BoxClaw CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Command: auth
    auth_parser = subparsers.add_parser("auth", help="Authentication tools")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")
    
    # Command: auth issue-token
    issue_parser = auth_subparsers.add_parser("issue-token", help="Issue a local mock token for testing")
    issue_parser.add_argument("--agent", required=True, help="Agent identifier")
    issue_parser.add_argument("--allowed", required=True, help="Comma-separated allowed capabilities")
    
    args = parser.parse_args()
    
    if args.command == "auth" and getattr(args, "auth_command") == "issue-token":
        capabilities = [c.strip() for c in args.allowed.split(",")]
        token = generate_mock_token(args.agent, capabilities)
        print(f"Generated locally signed mock token for {args.agent} (Expires in 15m):")
        print(f"\n{token}\n")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
