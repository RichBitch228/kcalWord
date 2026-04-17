import json
import anthropic

client = anthropic.Anthropic()

SYSTEM_PROMPT = """Ти — асистент для підрахунку калорій.
Користувач описує що він з'їв, а ти розраховуєш харчову цінність.
Відповідай ТІЛЬКИ валідним JSON без жодного іншого тексту.
Формат відповіді:
{
  "kcal": <ціле число>,
  "protein": <ціле число, грами>,
  "fat": <ціле число, грами>,
  "carbs": <ціле число, грами>,
  "foods": ["назва продукту 1", "назва продукту 2", ...]
}
Якщо маса не вказана — використовуй стандартну порцію.
Округляй до цілих чисел."""


def parse_food(text: str) -> dict:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    raw = message.content[0].text.strip()
    return json.loads(raw)
