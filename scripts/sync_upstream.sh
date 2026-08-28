#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source_checkout=""
upstream_ref="main"

while [ "$#" -gt 0 ]; do
	case "$1" in
		--source)
			source_checkout="$2"
			shift 2
			;;
		--ref)
			upstream_ref="$2"
			shift 2
			;;
		*)
			echo "usage: $0 [--source /path/to/cursor-plugins] [--ref git-ref]" >&2
			exit 2
			;;
	esac
done

temp_dir=""
cleanup() {
	if [ -n "$temp_dir" ] && [ -d "$temp_dir" ]; then
		rm -rf "$temp_dir"
	fi
}
trap cleanup EXIT

if [ -z "$source_checkout" ]; then
	temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/pstack-codex-sync.XXXXXX")
	source_checkout="$temp_dir/cursor-plugins"
	git clone --filter=blob:none --no-checkout https://github.com/cursor/plugins.git "$source_checkout"
	git -C "$source_checkout" sparse-checkout init --cone
	git -C "$source_checkout" sparse-checkout set pstack
	git -C "$source_checkout" checkout "$upstream_ref"
fi

python3 "$repo_root/scripts/port_upstream.py" "$source_checkout" --ref "$upstream_ref"
python3 "$repo_root/scripts/validate_port.py"

echo "synced pstack from $(git -C "$source_checkout" rev-parse --short HEAD)"
