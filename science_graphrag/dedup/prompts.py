from __future__ import annotations

SYSTEM_SAME_WORK = (
    "You decide whether two bibliographic records describe the same scholarly work.\n"
    "Answer conservatively: same work means same underlying publication "
    "(e.g. arXiv preprint and journal version count as the same).\n"
    "Return JSON matching the schema with same_work (boolean) and a short reason."
)

USER_SAME_WORK_TEMPLATE = """Work A:
- title: {title_a}
- year: {year_a}
- first_author: {first_author_a}
- abstract_excerpt: {abstract_a}

Work B:
- title: {title_b}
- year: {year_b}
- first_author: {first_author_b}
- abstract_excerpt: {abstract_b}

Are A and B the same work?"""


SYSTEM_SAME_AUTHOR = (
    "You decide whether two author records refer to the same person "
    "(same individual), not merely the same surname.\n"
    "Consider initials, transliteration, and affiliation hints.\n"
    "Return JSON with same_author and reason."
)

USER_SAME_AUTHOR_TEMPLATE = """Author A: {name_a} | affiliation hint: {aff_a}
Author B: {name_b} | affiliation hint: {aff_b}

Are A and B the same person?"""
