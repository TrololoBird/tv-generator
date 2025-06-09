import json
import re

def strip_timeframe(field):
    # Убирает суффикс таймфрейма (|что-угодно) и все скобки справа, если это не часть имени
    return field.split('|')[0].strip()

def main():
    # Загрузка данных
    with open("numeric_fields_no_timeframe.json", "r", encoding="utf-8") as f1:
        no_tf = set(json.load(f1))
    with open("numeric_fields_with_timeframe.json", "r", encoding="utf-8") as f2:
        with_tf = set(json.load(f2))

    # Уникальные базовые поля с таймфреймом
    base_fields_with_tf = set()
    for field in with_tf:
        if "|" in field:
            base = strip_timeframe(field)
            base_fields_with_tf.add(base)
        else:
            # safety: такие редко, но если что — тоже запишем
            base_fields_with_tf.add(field)

    # Всё что есть в no_timeframe, но нет в base_fields_with_tf — это точно только без таймфрейма
    only_no_tf = sorted(list(no_tf - base_fields_with_tf))
    only_with_tf = sorted(list(base_fields_with_tf))

    # Генерация YAML
    def to_yaml(name, items):
        s = f"{name}:\n  type: string\n  enum:\n"
        for val in items:
            s += f"    - {val}\n"
        return s

    with open("openapi_numeric_enums.yaml", "w", encoding="utf-8") as f:
        f.write("# --- Only fields WITHOUT timeframe ---\n")
        f.write(to_yaml("NumericFieldNoTimeframe", only_no_tf))
        f.write("\n# --- Only fields WITH timeframe ---\n")
        f.write(to_yaml("NumericFieldWithTimeframe", only_with_tf))
        f.write("\n")

    print("YAML saved to openapi_numeric_enums.yaml")

if __name__ == "__main__":
    main()
