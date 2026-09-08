#!/usr/bin/env bash
# Create one test user per Directus role so you can log in as each persona.
#
#   ./scripts/create_role_users.sh                 # create the 3 missing users
#   ./scripts/create_role_users.sh --reset-existing  # also reset editor@/sub@ passwords
#
# Reads ADMIN_EMAIL / ADMIN_PASSWORD from .env. Never touches modernflush@gmail.com.
set -euo pipefail

cd "$(dirname "$0")/.."
BASE="${BASE:-http://localhost:8057}"
set -a; . ./.env; set +a

# Password used for every test account. Change it here before running.
PW="${TEST_PASSWORD:-TFGBVdev!2026}"

TOKEN=$(curl -s -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "$(printf '{"email":"%s","password":"%s"}' "$ADMIN_EMAIL" "$ADMIN_PASSWORD")" \
  | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$TOKEN" ] || { echo "login failed - check ADMIN_EMAIL/ADMIN_PASSWORD in .env"; exit 1; }

role_id() {
  curl -s "$BASE/roles?filter[name][_eq]=$(printf %s "$1" | sed 's/ /%20/g')&fields=id" \
    -H "Authorization: Bearer $TOKEN" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p'
}

create_user() { # email, role name, first, last
  local email=$1 role=$2 fn=$3 ln=$4 rid
  rid=$(role_id "$role")
  [ -n "$rid" ] || { echo "  !! role not found: $role"; return; }
  local code
  code=$(curl -s -o /tmp/cru.out -w '%{http_code}' -X POST "$BASE/users" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "$(printf '{"email":"%s","password":"%s","role":"%s","first_name":"%s","last_name":"%s","status":"active"}' \
          "$email" "$PW" "$rid" "$fn" "$ln")")
  case "$code" in
    200|204) echo "  created  $email  ($role)" ;;
    400)     echo "  exists   $email  (skipped)" ;;
    *)       echo "  FAILED   $email  http=$code $(head -c 200 /tmp/cru.out)" ;;
  esac
}

reset_password() { # email
  local email=$1 uid
  uid=$(curl -s "$BASE/users?filter[email][_eq]=$email&fields=id" \
        -H "Authorization: Bearer $TOKEN" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p')
  [ -n "$uid" ] || { echo "  !! no such user: $email"; return; }
  curl -s -o /dev/null -X PATCH "$BASE/users/$uid" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d "$(printf '{"password":"%s"}' "$PW")"
  echo "  reset    $email"
}

echo "Creating missing role users on $BASE ..."
create_user "author@gmail.com"     "Author"      "Test"  "Author"
create_user "caseadmin@gmail.com"  "Admin"       "Case"  "Admin"
create_user "superadmin@gmail.com" "Super Admin" "Super" "Admin"

if [ "${1:-}" = "--reset-existing" ]; then
  echo "Resetting passwords for existing test users ..."
  reset_password "editor@gmail.com"
  reset_password "sub@gmail.com"
fi

echo
echo "Password for all accounts above: $PW"
echo "Log in at: $BASE/admin/login"
