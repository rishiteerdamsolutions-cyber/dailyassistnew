from bol.modules.m9_social.executor import SocialFlowExecutor
print("Executor loaded successfully")
import traceback
try:
    executor = SocialFlowExecutor()
    print("Executor initialized")
except Exception as e:
    traceback.print_exc()
