#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/image_watermark.py" --gui
fi

osascript -e 'display alert "未找到 python3" message "请先安装 Python 3，然后重新双击此启动文件。"' >/dev/null 2>&1
exit 1
