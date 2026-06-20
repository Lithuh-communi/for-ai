#!/usr/bin/env python3
"""skill-index.py v1.0 — Rikkahub Skill 索引扫描"""

import os, re

SKILLS_DIR = "/skills"

def parse_frontmatter(text):
    """解析 YAML frontmatter"""
    # 简单 frontmatter 解析（不需 yaml 库）
    result = {}
    in_fm = False
    for line in text.split('\n'):
        if line.strip() == '---':
            in_fm = not in_fm
            continue
        if in_fm and ':' in line:
            k, v = line.split(':', 1)
            result[k.strip()] = v.strip()
    return result

def scan_skills():
    if not os.path.exists(SKILLS_DIR):
        print(f"❌ Skills 目录不存在: {SKILLS_DIR}")
        return []

    skills = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        skill_dir = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(skill_dir):
            continue

        skill_md = os.path.join(skill_dir, "SKILL.md")
        status = "✅"
        warnings = []

        if not os.path.exists(skill_md):
            status = "❌"
            warnings.append("缺少 SKILL.md")
        else:
            with open(skill_md, 'r') as f:
                content = f.read()

            fm = parse_frontmatter(content)
            skill_name = fm.get('name', '')
            description = fm.get('description', '')

            if not skill_name:
                warnings.append("frontmatter 缺少 name")
            if not description:
                warnings.append("frontmatter 缺少 description")
            if skill_name and skill_name != name:
                warnings.append(f"目录名 '{name}' 与 name '{skill_name}' 不一致")

            # 检查是否被截断
            if content.count('---') < 2:
                warnings.append("frontmatter 未闭合（可能被截断）")

            # 检查文件大小
            size = len(content.encode('utf-8'))
            if size < 100:
                warnings.append(f"文件过小 ({size} bytes)")

        skills.append({
            'dir': name,
            'status': status,
            'warnings': warnings,
            'path': f"skills/{name}/SKILL.md"
        })

    return skills

def main():
    skills = scan_skills()
    good = sum(1 for s in skills if s['status'] == '✅')
    bad = len(skills) - good

    print(f"📋 Rikkahub Skill 索引 (共 {len(skills)} 个)")
    print("=" * 60)
    for s in skills:
        if s['warnings']:
            print(f"  ⚠️  {s['dir']:<25s} {s['path']}")
            for w in s['warnings']:
                print(f"      └─ {w}")
        else:
            print(f"  ✅  {s['dir']:<25s} {s['path']}")
    print("=" * 60)
    print(f"    {good} 个正常, {bad} 个有问题")

if __name__ == '__main__':
    main()
