from monitor.build import chart_sentences


def test_forecast_span_without_government_median_age_and_hicp():
    f = lambda by, d, v: {"by": by, "date": d, "values": v, "round": "Herbstprojektion 2099"}
    c = {"type": "forecast", "measure": "inflation", "forecasts": [
        f("Bundesregierung", "2099-10-08", {2099: 2.7}), f("Bundesbank (HVPI)", "2099-06-12", {2099: 2.9, 2100: 1.9}),
        f("ifo Institut", "2099-09-10", {2099: 2.8}), f("IWH", "2099-09-11", {2099: 2.6})]}
    assert chart_sentences(c) == [
        "Die Bundesregierung erwartet in ihrer Herbstprojektion 2099 eine Inflationsrate von 2,7 % für 2099.",
        "Die jüngsten Prognosen anderer Institutionen reichen für 2099 von 2,6 bis 2,9 % (drei Institutionen); für 2100 liegt nur eine vor (1,9 %).",
        "Im Mittel (Median) erwarten sie für 2099 2,8 %.",
        "Diese Prognosen stammen von Juni bis September 2099.",
        "Die Bundesbank rechnet mit dem EU-weit harmonisierten Verbraucherpreisindex, die übrigen mit dem Verbraucherpreisindex."]
