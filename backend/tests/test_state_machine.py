from app.state_machine import TrafficLightFSM

STEP = 0.25  # segundos entre analisis, como el monitor


def run(fsm, sequence, start=0.0):
    """Pasa (estado visual, segundos) por la FSM y devuelve cada estado y las anomalias que aparecieron."""
    now, states, anomalies = start, [], []
    for visual, seconds in sequence:
        for _ in range(round(seconds / STEP)):
            now += STEP
            status = fsm.update(visual, now=now)
            if status.confirmed_anomaly and status.confirmed_anomaly not in anomalies:
                anomalies.append(status.confirmed_anomaly)
        states.append(status.current_state)
    return states, anomalies, status


CYCLE = [("RED", 30), ("YELLOW", 3), ("GREEN", 20), ("YELLOW", 3)]


def test_normal_cycle_has_no_anomalies():
    states, anomalies, _ = run(TrafficLightFSM(), CYCLE * 2)
    assert states[:4] == ["ROJO", "AMARILLO_PREP", "VERDE", "AMARILLO_DESP"]
    assert anomalies == []


def test_yellow_lost_from_view_is_not_an_invalid_transition():
    _, anomalies, _ = run(TrafficLightFSM(), [("RED", 30), ("UNKNOWN", 3), ("GREEN", 20), ("YELLOW", 3), ("RED", 30)])
    assert anomalies == []


def test_invalid_transition_resyncs_and_clears_on_the_next_legal_change():
    fsm = TrafficLightFSM()
    states, anomalies, status = run(fsm, [("RED", 30), ("GREEN", 5)])
    assert (states[-1], status.confirmed_anomaly) == ("VERDE", "INVALID_TRANSITION")

    states, anomalies, status = run(fsm, [("YELLOW", 3), ("RED", 30)], start=35)
    assert states == ["AMARILLO_DESP", "ROJO"]
    assert status.confirmed_anomaly is None


def test_a_one_frame_flicker_is_ignored():
    _, anomalies, status = run(TrafficLightFSM(), [("GREEN", 10), ("OFF", 0.25), ("GREEN", 5)])
    assert (anomalies, status.current_state) == ([], "VERDE")


def test_lights_off_lasts_while_it_happens_and_does_not_break_the_sequence():
    fsm = TrafficLightFSM()
    _, anomalies, status = run(fsm, [("RED", 30), ("OFF", 3)])
    assert status.confirmed_anomaly == "ALL_LIGHTS_OFF"

    # Tras una falla no hay color previo confiable: volver en verde no es un salto ilegal
    states, anomalies, status = run(fsm, [("GREEN", 5)], start=33)
    assert "INVALID_TRANSITION" not in anomalies
    assert (states, status.confirmed_anomaly) == (["VERDE"], None)


def test_light_stuck_does_not_count_the_time_out_of_view():
    _, anomalies, _ = run(TrafficLightFSM(), [("RED", 100), ("UNKNOWN", 60), ("RED", 30)])
    assert anomalies == []

    _, anomalies, _ = run(TrafficLightFSM(), [("RED", 125)])
    assert anomalies == ["LIGHT_STUCK"]


def test_confirming_the_next_color_does_not_count_as_time_in_the_previous_one():
    # Amarillo de 4,5 s (maximo 5 s): el segundo que tarda en confirmarse el rojo no lo alarga
    _, anomalies, _ = run(TrafficLightFSM(), [("GREEN", 10), ("YELLOW", 4.5), ("RED", 5)])
    assert anomalies == []


def test_static_images_only_get_lights_off_and_multiple_lights():
    _, anomalies, _ = run(TrafficLightFSM(timing_rules=False), [("RED", 300)])
    assert anomalies == []

    _, anomalies, _ = run(TrafficLightFSM(timing_rules=False), [("MULTIPLE", 5)])
    assert anomalies == ["MULTIPLE_LIGHTS_ON"]


def test_reset_forgets_the_previous_color():
    fsm = TrafficLightFSM()
    run(fsm, [("RED", 5)])
    fsm.reset(now=5)
    _, anomalies, _ = run(fsm, [("GREEN", 5)], start=5)
    assert anomalies == []
