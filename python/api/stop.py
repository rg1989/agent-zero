from python.helpers.api import ApiHandler, Input, Output, Request, Response
from python.helpers.task_scheduler import TaskScheduler


class Stop(ApiHandler):
    """Stop the agent immediately without clearing chat history."""

    async def process(self, input: Input, request: Request) -> Output:
        ctxid = input.get("context", "")
        if not ctxid:
            raise Exception("No context id provided")

        # Cancel any scheduler tasks bound to this context
        TaskScheduler.get().cancel_tasks_by_context(ctxid, terminate_thread=True)

        # Get the context and kill the process (without resetting/clearing history)
        context = self.use_context(ctxid)
        context.kill_process()
        context.paused = False

        msg = "Agent stopped."
        context.log.log(type="info", content=msg)

        return {
            "message": msg,
            "ctxid": context.id,
        }
