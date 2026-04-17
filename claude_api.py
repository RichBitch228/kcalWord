import json
import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Ти — асистент для підрахунку калорій.
Якщо повідомлення містить їжу або продукти — розрахуй харчову цінність і відповідай ТІЛЬКИ валідним JSON:
{
  "is_food": true,
  "kcal": <ціле число>,
  "protein": <ціле число, грами>,
  "fat": <ціле число, грами>,
  "carbs": <ціле число, грами>,
  "foods": ["назва продукту 1", "назва продукту 2", ...]
}

Якщо повідомлення НЕ про їжу (привітання, питання, команди тощо) — відповідай JSON:
{
  "is_food": false,
  "reply": "<коротка дружня відповідь українською>"
}

Якщо маса не вказана — використовуй стандартну порцію. Округляй до цілих чисел.
Відповідай ТІЛЬКИ валідним JSON без жодного іншого тексту."""


def parse_food(text: str) -> dict:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
