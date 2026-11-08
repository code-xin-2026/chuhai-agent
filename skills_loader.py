"""技能库加载器：读取 skills/ 下的 SKILL.md，编译成 system prompt 上下文，并按需读参考资料。"""
import os

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills")


def _parse_skill(md_text):
    """解析 SKILL.md 的 frontmatter(name/description) + 正文。"""
    fm = {}
    body = md_text
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = parts[2].strip()
    return fm, body


def load_skills():
    """返回 [{name, description, body}, ...]，按名字排序。"""
    skills = []
    if not os.path.isdir(SKILLS_DIR):
        return skills
    for name in sorted(os.listdir(SKILLS_DIR)):
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if os.path.isfile(path):
            fm, body = _parse_skill(open(path, encoding="utf-8").read())
            skills.append({"name": fm.get("name", name),
                           "description": fm.get("description", ""), "body": body})
    return skills


def skills_context():
    """编译所有技能为一段注入 system prompt 的上下文。"""
    parts = []
    for s in load_skills():
        parts.append(f"## 技能「{s['name']}」\n{s['description']}\n\n{s['body']}")
    return "\n\n".join(parts)


def list_skill_names():
    return [s["name"] for s in load_skills()]


def read_reference(skill: str, ref: str = ""):
    """读取某技能下的参考资料（仅限 skills/ 目录内，防路径穿越）。"""
    skills_real = os.path.realpath(SKILLS_DIR)
    base = os.path.realpath(os.path.join(SKILLS_DIR, skill))
    if not base.startswith(skills_real + os.sep):
        return {"error": f"未知技能：{skill}"}

    target = os.path.realpath(os.path.join(base, ref)) if ref else base
    if not (target == skills_real or target.startswith(skills_real + os.sep)):
        return {"error": "路径越界，仅允许读取 skills/ 目录内文件"}

    if os.path.isdir(target):
        files = []
        for root, _dirs, fnames in os.walk(target):
            for fn in sorted(fnames):
                files.append(os.path.relpath(os.path.join(root, fn), base).replace("\\", "/"))
        return {"skill": skill, "files": files}

    if os.path.isfile(target):
        try:
            return {"skill": skill, "file": ref,
                    "content": open(target, encoding="utf-8").read()}
        except Exception as e:  # noqa: BLE001
            return {"error": f"读取失败：{e}"}

    return {"error": f"未找到 {skill}/{ref}"}
