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

    def test_unknown_challenges_property(self):
        self.assertTrue(
            at_line(self.issues, 108, "unknown challenges property"),
            "expected 'unknown challenges property' error at line 108",
        )

    def test_single_quoted_prop_value(self):
        # The "bogus" case on line 108 also fires the double-quote
        # check; the dedicated single-quote title prop is at line 114.
        self.assertTrue(
            at_line(self.issues, 108, "double quotes"),
            "expected 'double quotes' error at line 108",
        )
        self.assertTrue(
            at_line(self.issues, 115, "double quotes"),
            "expected 'double quotes' error at line 115",
        )

    def test_challenges_title_with_no_value(self):
        self.assertTrue(
            at_line(self.issues, 122, "has no value"),
            "expected 'has no value' error at line 122",
        )

    def test_issues_are_sorted_by_line(self):
        lines = [i["line"] for i in self.issues]
        self.assertEqual(lines, sorted(lines), "issues should be sorted by line")

    def test_each_expected_issue(self):
        # Each case in the fixture is pinned by line and a message
        # substring. A new case added to the fixture below must also be
        # added here, and removing one fails this test.
        expected = [
            (11, "unknown pressure-pool property: 'reload'"),
            (18, "unknown div class: 'foo'"),
            (25, "pressure-pool missing '## xD TITLE' heading"),
            (32, "challenges div has no challenge cards"),
            (37, "image div has no markdown image"),
            (43, "challenges div has no challenge cards"),
            (44, "heading missing dice notation: 'A Title Without Dice'"),
            (54, "trigger link '>>*' is not supported in challenges"),
            (64, "plain link '>' is not supported in pressure pools"),
            (77, "pressure-pool link target not found: 'Ghost Pool'"),
            (86, "duplicate challenge title: 'Same Name'"),
            (95, "dice value 0 outside 1..8 range"),
            (98, "dice value 9 outside 1..8 range"),
            (104, "closing ':::' with no matching opener"),
            (108, "unknown challenges property: 'bogus'"),
            (108, "prop must use double quotes: \"bogus='value'\""),
            (115, "prop must use double quotes: \"title='Wrong quotes'\""),
            (122, "challenges property 'title' has no value (use title=\"...\")"),
        ]
        actual = [(i["line"], i["message"]) for i in self.issues]
        self.assertEqual(
            actual,
            expected,
            "fixture issues do not match the expected list; "
            "update this test when adding or removing a case in the fixture.",
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
