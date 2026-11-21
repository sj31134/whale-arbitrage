"""
Skill Synthesizer: Automatically distills recurring analytical patterns, valuation heuristics, and sector playbooks into Antigravity Skills.
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class SkillSynthesizer:
    def __init__(self, workspace_skills_dir: Optional[str] = None):
        if workspace_skills_dir is None:
            # Locate .agents/skills at workspace root
            root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
            self.skills_dir = root_dir / ".agents" / "skills"
        else:
            self.skills_dir = Path(workspace_skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def synthesize_skill(
        self,
        skill_name: str,
        description: str,
        principles: List[Dict[str, str]],
        formulas_or_rules: List[str],
        case_studies: List[str]
    ) -> Path:
        """
        Creates or updates a standard Antigravity skill file.
        """
        target_dir = self.skills_dir / skill_name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        principles_md = ""
        for p in principles:
            principles_md += f"### • {p['title']}\n{p['content']}\n\n"

        rules_md = "\n".join([f"- {r}" for r in formulas_or_rules])
        cases_md = "\n".join([f"- **Case:** {c}" for c in case_studies])

        content = f"""---
name: {skill_name}
description: >-
  {description}
---

# {skill_name.replace('-', ' ').title()} Playbook & Heuristic Guidelines

Auto-distilled and crystallized from live investor agent research and knowledge graph updates.
Last Updated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

---

## 1. Core Operating Principles

{principles_md}

---

## 2. Quantitative Rules & Decision Triggers

{rules_md}

---

## 3. Ground-Truth Case Studies & Benchmarks

{cases_md}
"""

        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(content)

        return skill_file
