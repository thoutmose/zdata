from app.data.chat_lexicons import contains_any, leading_boundary_sql


def test_leading_boundary_sql_ors_every_word() -> None:
    sql = leading_boundary_sql("message_text", ["connard", "idiot"])
    assert sql == "CASE WHEN message_text ~* '\\y(connard|idiot)' THEN 1.0 ELSE 0.0 END"


def test_contains_any_is_case_insensitive() -> None:
    assert contains_any("MAIS TA GUEULE", ["ta gueule"])
    assert contains_any("quel idiot !", ["idiot"])


def test_contains_any_false_when_no_word_present() -> None:
    assert not contains_any("merci pour le stream", ["connard", "idiot"])


def test_contains_any_allows_trailing_inflection() -> None:
    # Plurals and emphasis-lengthened forms are still the same word — only
    # a *leading* boundary is required, confirmed against real chat data
    # where a trailing boundary silently dropped genuine repeats like
    # "CONNASSEEEE".
    assert contains_any("des connards partout", ["connard"])
    assert contains_any("CONNASSEEEE", ["connasse"])
    assert contains_any("elle est idiote", ["idiot"])


def test_contains_any_rejects_compound_word_false_positives() -> None:
    # Confirmed against real chat data: bare substring matching on "idiot"
    # also matched Twitch emote codes and username mentions with no real
    # word boundary before the match.
    assert not contains_any("melokaIdiot", ["idiot"])
    assert not contains_any("@je_un_idiot", ["idiot"])
    assert not contains_any("reconnecte", ["connard"])
