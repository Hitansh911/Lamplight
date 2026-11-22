import pytest

from journal.safety import Level, assess


@pytest.mark.parametrize(
    "text",
    [
        "I want to die",
        "I've been thinking about suicide",
        "Sometimes I think about killing myself",
        "i dont want to be alive anymore",
        "everyone would be better off without me",
        "I keep wanting to hurt myself",
        "mujhe khudkushi ke khayal aate hain",
        "ab jeene ka mann nahi karta",
        "मुझे आत्महत्या के विचार आते हैं",
        "I WANT TO DIE!!!",
        "i can’t go on",
    ],
)
def test_crisis_phrases(text):
    assert assess(text, mood=3).level == Level.CRISIS


@pytest.mark.parametrize(
    "text",
    [
        "I'm so stressed about exams and overwhelmed, I can't sleep",
        "I feel hopeless and worthless after my result",
        "had a panic attack in the library, feeling anxious",
        "bahut tension hai, neend nahi aa rahi",
    ],
)
def test_distress_phrases(text):
    result = assess(text, mood=3)
    assert result.level == Level.DISTRESS
    assert result.needs_helpline


def test_low_mood_plus_one_stress_word_is_distress():
    assert assess("Quite stressed today.", mood=2).level == Level.DISTRESS


def test_heaviest_mood_alone_shows_helplines():
    assert assess("Not a great day.", mood=1).needs_helpline


@pytest.mark.parametrize(
    "text",
    [
        "Had a good day. Finished my assignment and went for a walk with friends.",
        "I'm dying of embarrassment, I called the professor mom",
        "We killed it in the hackathon!",
    ],
)
def test_ordinary_entries_are_ok(text):
    assert assess(text, mood=4).level == Level.OK


def test_crisis_wins_over_mood_and_other_words():
    assert assess("great day but I want to die", mood=5).level == Level.CRISIS
