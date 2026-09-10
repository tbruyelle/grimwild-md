"""Tests for grimwild.validate().

Run with: python3 -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import grimwild

ROOT = Path(__file__).parent.parent
FIXTURE = Path(__file__).parent / "validate-fixture.md"


def at_line(issues, line, substring):
    return [i for i in issues if i["line"] == line and substring in i["message"]]


class FixtureTest(unittest.TestCase):
    """Each fenced block in validate-fixture.md exercises one case. The
    expected issues are pinned by line; add a new case at the bottom of
    the fixture so earlier line numbers stay stable."""

    @classmethod
    def setUpClass(cls):
        cls.issues = grimwild.validate(FIXTURE.read_text(encoding="utf-8"))

    def test_unknown_pool_property(self):
        self.assertTrue(
            at_line(self.issues, 11, "unknown pressure-pool property"),
            "expected 'unknown pressure-pool property' error at line 11",
        )

    def test_unknown_div_class(self):
        self.assertTrue(
            at_line(self.issues, 18, "unknown div class"),
            "expected 'unknown div class' error at line 18",
        )

    def test_pressure_pool_missing_heading(self):
        self.assertTrue(
            at_line(self.issues, 25, "pressure-pool missing"),
            "expected 'pressure-pool missing heading' error at line 25",
        )

    def test_challenges_div_with_no_cards(self):
        self.assertTrue(
            at_line(self.issues, 32, "no challenge cards"),
            "expected 'no challenge cards' error at line 32",
        )

    def test_image_div_with_no_image(self):
        self.assertTrue(
            at_line(self.issues, 37, "no markdown image"),
            "expected 'no markdown image' error at line 37",
        )

    def test_heading_without_dice(self):
        # The challenges div at line 43 has a malformed heading, so it
        # both fails the dice check and (post-pass) has no valid cards.
        self.assertTrue(
            at_line(self.issues, 44, "heading missing dice notation"),
            "expected 'heading missing dice notation' error at line 44",
        )
        self.assertTrue(
            at_line(self.issues, 43, "no challenge cards"),
            "expected 'no challenge cards' error at line 43",
        )

    def test_trigger_link_in_challenges(self):
        self.assertTrue(
            at_line(self.issues, 54, "trigger link"),
            "expected 'trigger link' error at line 54",
        )

    def test_plain_link_in_pool(self):
        self.assertTrue(
            at_line(self.issues, 64, "plain link"),
            "expected 'plain link' error at line 64",
        )

    def test_pool_link_to_nonexistent_target(self):
        self.assertTrue(
            at_line(self.issues, 77, "pressure-pool link target not found"),
            "expected 'pressure-pool link target not found' error at line 77",
        )

    def test_duplicate_challenge_title(self):
        self.assertTrue(
            at_line(self.issues, 86, "duplicate challenge title"),
            "expected 'duplicate challenge title' error at line 86",
        )

    def test_dice_value_below_range(self):
        self.assertTrue(
            at_line(self.issues, 95, "outside 1..8"),
            "expected 'outside 1..8' error at line 95",
        )

    def test_dice_value_above_range(self):
        self.assertTrue(
            at_line(self.issues, 98, "outside 1..8"),
            "expected 'outside 1..8' error at line 98",
        )

    def test_orphan_closing_fence(self):
        self.assertTrue(
            at_line(self.issues, 104, "no matching opener"),
            "expected 'no matching opener' error at line 104",
        )

    def test_fixture_produces_no_unexpected_issues(self):
        self.assertEqual(
            len(self.issues),
            14,
            f"unexpected issue count: {[i for i in self.issues]}",
        )


class RealModulesTest(unittest.TestCase):
    """The shipped modules must validate clean, so a typo in a future
    edit shows up in the build before it shows up in the PDF."""

    def _validate(self, name):
        return grimwild.validate((ROOT / name).read_text(encoding="utf-8"))

    def test_plague_of_goblins_is_clean(self):
        self.assertEqual(self._validate("plague-of-goblins.md"), [])

    def test_pas_de_fumee_sans_feu_is_clean(self):
        self.assertEqual(self._validate("pas-de-fumee-sans-feu.md"), [])


class EdgeCaseTest(unittest.TestCase):
    def test_empty_source(self):
        self.assertEqual(grimwild.validate(""), [])

    def test_blank_source(self):
        self.assertEqual(grimwild.validate("\n\n\n"), [])

    def test_title_only(self):
        self.assertEqual(grimwild.validate("# Title\n\nIntro.\n"), [])

    def test_lone_closing_fence(self):
        issues = grimwild.validate(":::\n")
        self.assertEqual(len(issues), 1)
        self.assertIn("no matching opener", issues[0]["message"])

    def test_lone_unclosed_fence(self):
        issues = grimwild.validate("::: {.pressure-pool}\n")
        # Both errors fire: the fence is unclosed AND the pool has no
        # heading. The user fixes the unclosed fence first and the
        # missing-heading check will rerun on the next build.
        self.assertEqual(len(issues), 2)
        self.assertTrue(any("unclosed" in i["message"] for i in issues))
        self.assertTrue(any("missing" in i["message"] for i in issues))

    def test_dice_value_1_is_accepted(self):
        # 1D is the lower bound; only 0D should fail.
        issues = grimwild.validate(
            "::: {.challenges}\n## 1D | Boundary\n* trait\n:::\n"
        )
        self.assertEqual(issues, [])


def _valid_section():
    """The "Valid syntax" section in the fixture: well-formed examples
    that must produce zero issues."""
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    start = next(
        i for i, line in enumerate(lines, start=1)
        if line == "## Valid syntax (no issues expected)"
    )
    return "\n".join(lines[start - 1:]) + "\n"


class ValidSyntaxTest(unittest.TestCase):
    """Each block in the fixture's 'Valid syntax' section exercises a
    positive case: it must round-trip the validator with no issues. If
    the validator starts rejecting one of these, the section needs an
    update or the validator has a regression."""

    def test_full_valid_section_passes(self):
        issues = grimwild.validate(_valid_section())
        self.assertEqual(
            issues, [],
            f"valid section produced unexpected issues: {issues}",
        )


if __name__ == "__main__":
    unittest.main()
