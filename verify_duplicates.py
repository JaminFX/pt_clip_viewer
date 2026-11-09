"""Reproduce merged-track re-adds and verify clipboard deduplication + notices."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clip_duplicates import new_lines, unique_lines
import pt_clip_viewer as viewer

A = "00:09:58:04-00:13:11:18"
B = "00:40:27:23-00:42:37:05"
RAW = ["00:09:58:04-00:10:00:15", "00:10:00:15-00:13:11:18",
       "00:40:27:23-00:40:30:05", "00:40:30:05-00:42:37:05"]


class RangeTests(unittest.TestCase):
    def test_stable_exact_duplicates_and_spacing(self):
        self.assertEqual(unique_lines([A, B, A, ' ' + B.replace('-', ' - ') + ' ']), ([A, B], 2))

    def test_raw_clips_inside_merged_ranges_are_duplicates(self):
        self.assertEqual(new_lines([A, B], RAW), ([], 4))

    def test_existing_adjacent_clips_cover_a_merged_range(self):
        self.assertEqual(new_lines(RAW, [A, B]), ([], 2))

    def test_gaps_and_partial_overlaps_are_preserved(self):
        existing = ["00:00:01:00-00:00:02:00", "00:00:03:00-00:00:04:00"]
        incoming = ["00:00:01:00-00:00:04:00", "00:00:00:00-00:00:02:00"]
        self.assertEqual(new_lines(existing, incoming), (incoming, 0))

    def test_duplicates_in_one_incoming_track_are_removed(self):
        self.assertEqual(new_lines([], [A, A, B, B]), ([A, B], 2))


def run_duplicate_checks(app):
    """Exercise production methods inside the frozen app on both Mac CPUs too."""
    slot = app._slot_widgets[0]
    data, lb = slot['data'], slot['listbox']
    app.tracks = [{'track_name': 'Reading_2', 'clips': [dict(zip(('start', 'end'), line.split('-'))) for line in RAW]}]
    app.view_idx = 0
    with patch.object(app, '_show_merge_dialog', return_value='merge'), \
            patch.object(viewer.messagebox, 'showinfo') as notice:
        app._slot_add_current(data, lb)
        if data['clips'] != [A, B]:
            raise RuntimeError('Initial adjacent merge failed')
        history = len(data['undo'])
        app._slot_add_current(data, lb)
        if data['clips'] != [A, B] or list(lb.get(0, 'end')) != [A, B]:
            raise RuntimeError('Merged track was added twice')
        if len(data['undo']) != history or notice.call_count != 1:
            raise RuntimeError('Duplicate-only add changed undo history or lost popup')
        if notice.call_args.args[0] != '检测到重复片段':
            raise RuntimeError('Duplicate popup was not displayed')

        # Historical broken state as in the screenshot: clean on the next add,
        # and retain an undo snapshot of precisely what was changed.
        app._slot_restore(data, lb, [A, B, A, B])
        app._slot_add_current(data, lb)
        if data['clips'] != [A, B] or data['undo'][-1] != [A, B, A, B]:
            raise RuntimeError('Legacy duplicate cleanup/undo failed')

        # Final-copy safety net. Same times under different headings remain in
        # their own groups; duplicates within a heading never reach clipboard.
        app._slot_restore(data, lb, [A, B, A, B])
        data['enabled'].set(True)
        for other in app._slots[1:]:
            other['enabled'].set(False)
        notice.reset_mock()
        app._edit_copy_all()
        app.update()
        output = app.clipboard_get()
        if output.count(A) != 1 or output.count(B) != 1 or notice.call_count != 1:
            raise RuntimeError('Group copy did not deduplicate with a popup')
        other = app._slot_widgets[1]
        other['data']['enabled'].set(True)
        app._slot_restore(other['data'], other['listbox'], [A])
        app._edit_copy_all()
        app.update()
        if app.clipboard_get().count(A) != 2:
            raise RuntimeError('Deduplication changed distinct group ownership')

        # All copy routes, including the single-track merge route.
        app.tracks[0]['clips'] = [dict(zip(('start', 'end'), line.split('-'))) for line in [A, B, A]]
        notice.reset_mock()
        app._copy_single()
        app.update()
        if app.clipboard_get().count(A) != 1 or notice.call_count != 1:
            raise RuntimeError('Single-track copy did not deduplicate with a popup')
        notice.reset_mock()
        text = app._clips_to_text(app.tracks[0]['clips'])
        if text.count(A) != 1 or notice.call_count != 1:
            raise RuntimeError('Multi-track copy did not deduplicate with a popup')

    # Restore an empty editor for the subsequent visual test/demo load.
    app.tree.delete(*app.tree.get_children())
    app.tracks, app.view_idx, app.selected_set = [], None, set()
    for index, slot in enumerate(app._slot_widgets):
        d = slot['data']
        app._slot_restore(d, slot['listbox'], [])
        d['undo'].clear()
        d['redo'].clear()
        d['enabled'].set(index == 0)
        app._slot_refresh_ur_buttons(d)
        app._refresh_slot_action_btns(d)
    print('PASS: merged re-add / legacy duplicates / popup / undo / clipboard routes.')


class DuplicateIntegrationTests(unittest.TestCase):
    def test_production_add_and_copy_routes(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(viewer, '_get_config_path', return_value=Path(tmp) / 'new.ini'), \
                patch.object(viewer, 'legacy_config_path', return_value=Path(tmp) / 'old.ini'):
            app = viewer.App()
            try:
                run_duplicate_checks(app)
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main(verbosity=2)
