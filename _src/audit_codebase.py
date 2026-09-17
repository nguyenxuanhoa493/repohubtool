#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive Code Audit & Quality Check for RetroHub."""

import os
import sys
import ast
import re
import py_compile

def run_audit():
    print('=' * 70)
    print(' 🔍 RETROHUB CODEBASE AUDIT & HEALTH CHECK ')
    print('=' * 70)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rh_dir = os.path.join(base_dir, 'files', 'rh')

    if not os.path.isdir(rh_dir):
        print(f'[-] Directory not found: {rh_dir}')
        return False

    files_checked = 0
    parse_errors = []
    bare_excepts = []
    security_warnings = []

    for root, _, files in os.walk(rh_dir):
        for f in sorted(files):
            if not f.endswith('.py'):
                continue
            
            files_checked += 1
            rel_path = os.path.relpath(os.path.join(root, f), base_dir)
            full_path = os.path.join(root, f)

            # 1. Bytecode compilation & AST check
            try:
                py_compile.compile(full_path, doraise=True)
                with open(full_path, 'r', encoding='utf-8') as fh:
                    content_str = fh.read()
                ast.parse(content_str, filename=full_path)
            except Exception as e:
                parse_errors.append((rel_path, str(e)))
                continue

            # 2. Line-by-line inspection
            for lineno, line in enumerate(content_str.splitlines(), 1):
                if re.match(r'^\s*except\s*:', line):
                    bare_excepts.append((rel_path, lineno, line.strip()))
                if re.search(r'(eval|exec)\s*\(', line) and not line.strip().startswith('#'):
                    security_warnings.append((rel_path, lineno, 'Dynamic code execution', line.strip()))

    print(f'[*] Tổng số file Python đã phân tích: {files_checked}')
    print('-' * 70)

    if parse_errors:
        print(f'[!] ❌ Lỗi cú pháp / AST: {len(parse_errors)}')
        for path, err in parse_errors:
            print(f'    - {path}: {err}')
    else:
        print('[+] ✅ 100% tất cả file Python đều vượt qua biên dịch cú pháp và AST.')

    if bare_excepts:
        print(f'[!] ⚠️ Còn bare except: {len(bare_excepts)}')
        for path, line, text in bare_excepts:
            print(f'    - {path}:{line} -> {text}')
    else:
        print('[+] ✅ Không còn bất kỳ khối bare except nào trong toàn bộ mã nguồn.')

    if security_warnings:
        print(f'[!] ⚠️ Cảnh báo bảo mật: {len(security_warnings)}')
        for path, line, desc, text in security_warnings:
            print(f'    - {path}:{line} [{desc}] -> {text}')
    else:
        print('[+] ✅ Không phát hiện hàm nguy hiểm eval()/exec() nào.')

    print('=' * 70)
    all_passed = (len(parse_errors) == 0 and len(bare_excepts) == 0)
    if all_passed:
        print(' 🎉 AUDIT RESULT: PASSED (MÃ NGUỒN ĐẠT CHUẨN TỐT 100%!)')
    else:
        print(' ❌ AUDIT RESULT: FAILED')
    print('=' * 70)
    return all_passed

if __name__ == '__main__':
    success = run_audit()
    sys.exit(0 if success else 1)
