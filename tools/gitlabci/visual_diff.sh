#!/usr/bin/env bash

set -e

# Root of the kicad-library-utils repo
klu_dir=$(realpath $(dirname ${BASH_SOURCE[0]})/../..)

base_commit="master"
target_commit="HEAD"
repo_dir=""
output_dir="diffs"
open_result=false


# usage: This function displays the usage information for the script.
# It provides a brief description of the script's purpose and the
# required/optional arguments that need to be passed to it.
# The function is typically called when the script is executed with
# incorrect or missing arguments, or when the user requests help.
usage() {
    echo "Usage: $0 [-r repo_dir] [-b base_sha] [-t target_sha] [-o output_dir] -- [html_diff_args ....]"
    echo "  -r repo_dir         Directory of the repository to compare"
    echo "  -b base_commit      Base commit SHA for the comparison (default: master)"
    echo "  -t target_commit    Target commit SHA for the comparison (default: HEAD)"
    echo "  -o output_dir       Directory to store the output diffs (default: diffs)"
    echo ""
    echo "  html_diff_args       Additional arguments for html_diff.py (e.g. -S /tmp/svg-out-dir)"
}

# Parse command line arguments
while getopts "r:b:t:o:O-" opt; do
    case ${opt} in
        r )
            repo_dir=$OPTARG
            ;;
        b )
            base_sha=$OPTARG
            ;;
        t )
            target_sha=$OPTARG
            ;;
        o )
            output_dir=$OPTARG
            ;;
        O)
            open_result=true
            ;;
        -) # on --, we're done with our own options
            break
            ;;
        \? )
            usage
            exit 1
            ;;
    esac
done

# Collect additional arguments for html_diff
shift $((OPTIND -1))
html_diff_args=("$@")

# Check if all required arguments are provided
if [ -z "$repo_dir" ] || [ -z "$base_sha" ] || [ -z "$target_sha" ] || [ -z "$output_dir" ]; then
    echo "Missing required arguments"
    usage
    exit 1
fi

# Run html_diff in git commit-commit mode
python3 "$klu_dir/html-diff/src/html_diff.py" \
    -j0 \
    --repo "$repo_dir" \
    --output "$output_dir" \
    "$base_sha" "$target_sha" \
    "${html_diff_args[@]}"
