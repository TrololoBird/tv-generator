import json

# Загрузка файлов
with open('base_indicators.json') as f:
    base_indicators = set(json.load(f))

with open('indicators_with_timeframe.json') as f:
    indicators_with_timeframe = json.load(f)

# Получение уникальных индикаторов из "with_timeframe", удаляя таймфрейм
indicators_with_tf_names = {k.split("|")[0] for k in indicators_with_timeframe}

# Категории
indicators_without_timeframes = sorted(base_indicators - indicators_with_tf_names)
indicators_with_timeframes = sorted(base_indicators & indicators_with_tf_names)

# Сохранение
with open("filtered_indicators_without_timeframes.json", "w") as f:
    json.dump(indicators_without_timeframes, f, indent=2)

with open("filtered_indicators_with_timeframes.json", "w") as f:
    json.dump(indicators_with_timeframes, f, indent=2)
