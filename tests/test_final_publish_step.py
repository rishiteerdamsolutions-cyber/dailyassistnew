from bol.modules.m9_social.flows import FLOW_REGISTRY, final_publish_step, ActionType


def test_final_publish_step_is_last_click_before_confirm():
    flow = FLOW_REGISTRY["facebook_post"]
    final = final_publish_step(flow)
    assert final is not None
    assert final.template == "facebook_s8_post_button"
    assert flow.steps[-1].action.value == "confirm_done"


def test_whatsapp_status_final_is_press_enter():
    flow = FLOW_REGISTRY["whatsapp_status"]
    final = final_publish_step(flow)
    assert final is not None
    assert final.action == ActionType.PRESS_ENTER
