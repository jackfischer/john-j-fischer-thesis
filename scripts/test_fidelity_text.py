"""Adversarial checks: errors the fidelity audit must catch, not generator tests."""
import copy
import unittest

from fidelity_text import add_line, compare


def stream(text):
    return {'body':[{'c':c,'id':f'fixture:{i}'} for i,c in enumerate(text)]}


class FidelityCorruptionTests(unittest.TestCase):
    def assert_rejected(self,before,after):
        self.assertFalse(all(r['passed'] for r in compare('mutation',stream(before),stream(after))))

    def test_date_digit(self): self.assert_rejected('April 15, 2023','April 15, 2028')
    def test_standalone_number(self): self.assert_rejected('volume 3, page 14','volume 8, page 14')
    def test_ordinal(self): self.assert_rejected('2nd-10th centuries','2th-10th centuries')
    def test_omitted_sentence(self): self.assert_rejected('First. Second. Third.','First. Third.')
    def test_reordered_words(self): self.assert_rejected('belief and affect','affect and belief')
    def test_reordered_paragraphs(self): self.assert_rejected('A first paragraph.\nA second paragraph.','A second paragraph.\nA first paragraph.')
    def test_case(self): self.assert_rejected('Free World','free world')
    def test_punctuation(self): self.assert_rejected('not, necessarily','not necessarily')
    def test_word_merge(self): self.assert_rejected('the rapist','therapist')
    def test_word_split(self): self.assert_rejected('therapist','the rapist')

    def test_wrong_note_attachment(self):
        before=stream('Two distinct claims.')
        before['body'].insert(3,{'c':'','anchor':'note:ch1:1'})
        after=copy.deepcopy(before)
        marker=after['body'].pop(3)
        after['body'].insert(12,marker)
        self.assertFalse(compare('mutation',before,after)[0]['passed'])

    def test_swapped_note_bodies(self):
        before=stream('Text')|{'note:ch1:1':stream('First citation')['body'],
                               'note:ch1:2':stream('Second citation')['body']}
        after=copy.deepcopy(before)
        after['note:ch1:1'],after['note:ch1:2']=after['note:ch1:2'],after['note:ch1:1']
        self.assertEqual(sum(not r['passed'] for r in compare('mutation',before,after)),2)

    def test_missing_and_extra_stream(self):
        before=stream('Text')|{'note:ch1:1':stream('Citation')['body']}
        self.assertTrue(any(not r['passed'] for r in compare('mutation',before,stream('Text'))))
        self.assertTrue(any(not r['passed'] for r in compare('mutation',stream('Text'),before)))

    def test_source_confirmed_physical_hyphen(self):
        before=stream('A contemporary scholar.')
        after=stream('A contem-porary scholar.')
        after['body'][8]['eol_hyphen']=True
        self.assertTrue(compare('layout',before,after,book=True)[0]['passed'])
        # A real internal hyphen cannot silently disappear.
        self.assert_rejected('belief-oriented','belieforiented')

    def test_curly_quotes_and_ligatures(self):
        self.assertTrue(compare('typography',stream('“office”'),stream('"ofﬁce"'))[0]['passed'])

    def test_italic_loss(self):
        before=stream('emphasis')
        for glyph in before['body']:glyph['style']='i'
        self.assertFalse(compare('style',before,stream('emphasis'))[0]['passed'])


if __name__=='__main__':unittest.main()
