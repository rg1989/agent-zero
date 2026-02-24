import asyncio
import time
from typing import Optional, cast
from agent import Agent, InterventionException
from pathlib import Path

from python.helpers.tool import Tool, Response
from python.helpers import files, defer, persist_chat, strings
from python.helpers.browser_use import browser_use  # type: ignore[attr-defined]
from python.helpers.print_style import PrintStyle
from python.helpers.playwright import ensure_playwright_binary
from python.helpers.secrets import get_secrets_manager
from python.extensions.message_loop_start._10_iteration_no import get_iter_no
from pydantic import BaseModel
import uuid
from python.helpers.dirty_json import DirtyJson


SHARED_BROWSER_CDP = "http://localhost:9222"
SHARED_BROWSER_CDP_PORT = 9222
SHARED_BROWSER_CDP_TIMEOUT = 20  # seconds to wait for Chromium to start


async def _wait_for_cdp(timeout: int = SHARED_BROWSER_CDP_TIMEOUT) -> bool:
    """Poll the CDP port until Chromium is ready or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", SHARED_BROWSER_CDP_PORT),
                timeout=2,
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return True
        except Exception:
            await asyncio.sleep(1)
    return False


class State:
    @staticmethod
    async def create(agent: Agent, use_shared: bool = False):
        state = State(agent, use_shared=use_shared)
        return state

    def __init__(self, agent: Agent, use_shared: bool = False):
        self.agent = agent
        self.use_shared = use_shared
        self.browser_session: Optional[browser_use.BrowserSession] = None
        self.task: Optional[defer.DeferredTask] = None
        self.use_agent: Optional[browser_use.Agent] = None
        self.secrets_dict: Optional[dict[str, str]] = None
        self.iter_no = 0

    def __del__(self):
        self.kill_task()
        if not self.use_shared:
            files.delete_dir(self.get_user_data_dir()) # cleanup user data dir

    def get_user_data_dir(self):
        return str(
            Path.home()
            / ".config"
            / "browseruse"
            / "profiles"
            / f"agent_{self.agent.context.id}"
        )

    async def _initialize(self):
        if self.browser_session:
            # Session exists from a previous task — ensure it is still connected.
            # start() is idempotent: returns immediately if already connected,
            # or reconnects if the CDP/Playwright link was lost.
            await self.browser_session.start()
            return

        if self.use_shared:
            # Connect to the visible shared browser running in the side panel.
            # Viewport matches the 420px drawer so sites render their native
            # mobile/responsive layout rather than a scaled-down desktop view.
            self.browser_session = browser_use.BrowserSession(
                cdp_url=SHARED_BROWSER_CDP,
                browser_profile=browser_use.BrowserProfile(
                    accept_downloads=True,
                    downloads_path=files.get_abs_path("usr/downloads"),
                    keep_alive=True,
                    minimum_wait_page_load_time=1.0,
                    wait_for_network_idle_page_load_time=2.0,
                    maximum_wait_page_load_time=10.0,
                    viewport={"width": 420, "height": 800},
                ),
            )
        else:
            # for some reason we need to provide exact path to headless shell, otherwise it looks for headed browser
            pw_binary = ensure_playwright_binary()

            self.browser_session = browser_use.BrowserSession(
                browser_profile=browser_use.BrowserProfile(
                    headless=True,
                    disable_security=True,
                    chromium_sandbox=False,
                    accept_downloads=True,
                    downloads_path=files.get_abs_path("usr/downloads"),
                    allowed_domains=["*", "http://*", "https://*"],
                    executable_path=pw_binary,
                    keep_alive=True,
                    minimum_wait_page_load_time=1.0,
                    wait_for_network_idle_page_load_time=2.0,
                    maximum_wait_page_load_time=10.0,
                    window_size={"width": 1024, "height": 2048},
                    screen={"width": 1024, "height": 2048},
                    viewport={"width": 1024, "height": 2048},
                    no_viewport=False,
                    args=["--headless=new"],
                    # Use a unique user data directory to avoid conflicts
                    user_data_dir=self.get_user_data_dir(),
                    extra_http_headers=self.agent.config.browser_http_headers or {},
                )
            )

        await self.browser_session.start() if self.browser_session else None
        # self.override_hooks()

        # --------------------------------------------------------------------------
        # Patch to enforce vertical viewport size
        # --------------------------------------------------------------------------
        # Browser-use auto-configuration overrides viewport settings, causing wrong
        # aspect ratio. We fix this by directly setting viewport size after startup.
        # --------------------------------------------------------------------------

        if self.browser_session:
            try:
                page = await self.browser_session.get_current_page()
                if page:
                    # Shared browser matches the 420px drawer; headless uses a
                    # tall viewport for scrolling/reading long pages.
                    vp = {"width": 420, "height": 800} if self.use_shared else {"width": 1024, "height": 2048}
                    await page.set_viewport_size(vp)
            except Exception as e:
                PrintStyle().warning(f"Could not force set viewport size: {e}")

        # --------------------------------------------------------------------------

        # Add init script to the browser session (skip for shared browser — context already live)
        if not self.use_shared and self.browser_session and self.browser_session.browser_context:
            js_override = files.get_abs_path("lib/browser/init_override.js")
            await self.browser_session.browser_context.add_init_script(path=js_override) if self.browser_session else None

    def start_task(self, task: str):
        if self.task and self.task.is_alive():
            self.kill_task()

        self.task = defer.DeferredTask(
            thread_name="BrowserAgent" + self.agent.context.id
        )
        if self.agent.context.task:
            # Use terminate_thread=False so the browser event loop (and its
            # Playwright global objects) survives between A0 message cycles.
            # The event loop is a daemon thread and will be cleaned up on exit.
            self.agent.context.task.add_child_task(self.task, terminate_thread=False)
        self.task.start_task(self._run_task, task) if self.task else None
        return self.task

    def kill_task(self):
        # Signal the browser-use agent to stop gracefully before cancelling coroutines.
        if self.use_agent:
            try:
                self.use_agent.state.stopped = True
            except Exception:
                pass

        if self.task:
            loop = getattr(self.task.event_loop_thread, 'loop', None)
            if loop and loop.is_running():
                # Cancel running asyncio coroutines (browser_use tasks) WITHOUT
                # terminating the event loop.  This keeps GLOBAL_PLAYWRIGHT_API_OBJECT
                # valid so the next task doesn't need to spawn a new Playwright subprocess.
                try:
                    drain_future = asyncio.run_coroutine_threadsafe(
                        defer.DeferredTask._drain_event_loop_tasks(), loop
                    )
                    drain_future.result(timeout=5.0)
                except Exception:
                    pass

                # For non-shared mode: close the headless browser session while the
                # event loop is still alive (avoids spawning a throwaway loop).
                if not self.use_shared and self.browser_session:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.browser_session.close(), loop
                        ).result(timeout=5.0)
                    except Exception:
                        pass
                    self.browser_session = None

            # Preserve the event loop (terminate_thread=False) so Playwright globals
            # remain valid for the next browser_agent call in this context.
            self.task.kill(terminate_thread=False)
            self.task = None

        # For shared mode: keep browser_session alive — keep_alive=True means
        # close() is a no-op anyway, and the session can be reused as-is.
        # For non-shared mode without a running loop: fall back to a new loop.
        if not self.use_shared and self.browser_session:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.browser_session.close())
                loop.close()
            except Exception as e:
                PrintStyle().error(f"Error closing browser session: {e}")
            finally:
                self.browser_session = None

        self.use_agent = None
        self.iter_no = 0

    async def _run_task(self, task: str):
        await self._initialize()

        class DoneResult(BaseModel):
            title: str
            response: str
            page_summary: str

        # Initialize controller
        controller = browser_use.Controller(output_model=DoneResult)

        # Register custom completion action with proper ActionResult fields
        @controller.registry.action("Complete task", param_model=DoneResult)
        async def complete_task(params: DoneResult):
            result = browser_use.ActionResult(
                is_done=True, success=True, extracted_content=params.model_dump_json()
            )
            return result

        model = self.agent.get_browser_model()

        try:

            secrets_manager = get_secrets_manager(self.agent.context)
            secrets_dict = secrets_manager.load_secrets()

            self.use_agent = browser_use.Agent(
                task=task,
                browser_session=self.browser_session,
                llm=model,
                use_vision=self.agent.config.browser_model.vision,
                extend_system_message=self.agent.read_prompt(
                    "prompts/browser_agent.system.md"
                ),
                controller=controller,
                enable_memory=False,  # Disable memory to avoid state conflicts
                sensitive_data=cast(dict[str, str | dict[str, str]] | None, secrets_dict or {}),  # Pass secrets
            )
        except Exception as e:
            raise Exception(
                f"Browser agent initialization failed. This might be due to model compatibility issues. Error: {e}"
            ) from e

        self.iter_no = get_iter_no(self.agent)

        async def hook(agent: browser_use.Agent):
            await self.agent.wait_if_paused()
            if self.iter_no != get_iter_no(self.agent):
                raise InterventionException("Task cancelled")

        # try:
        result = None
        if self.use_agent:
            result = await self.use_agent.run(
                max_steps=50, on_step_start=hook, on_step_end=hook
            )
        return result

    async def get_page(self):
        if self.use_agent and self.browser_session:
            try:
                return await self.use_agent.browser_session.get_current_page() if self.use_agent.browser_session else None
            except Exception:
                # Browser session might be closed or invalid
                return None
        return None

    async def get_selector_map(self):
        """Get the selector map for the current page state."""
        if self.use_agent:
            await self.use_agent.browser_session.get_state_summary(cache_clickable_elements_hashes=True) if self.use_agent.browser_session else None
            return await self.use_agent.browser_session.get_selector_map() if self.use_agent.browser_session else None
            await self.use_agent.browser_session.get_state_summary(
                cache_clickable_elements_hashes=True
            )
            return await self.use_agent.browser_session.get_selector_map()
        return {}


class BrowserAgent(Tool):

    async def execute(self, message="", reset="", use_shared="", **kwargs):
        self.guid = self.agent.context.generate_id() # short random id
        reset = str(reset).lower().strip() == "true"
        use_shared_bool = str(use_shared).lower().strip() == "true"

        if use_shared_bool:
            # Auto-start the shared browser app only if Chromium CDP is not reachable.
            # We check the actual CDP port rather than AppManager status, because the
            # status can be stale (e.g. if the tracked PID differs from the real Flask
            # process after a restart).  Restarting when Chromium is already running
            # would kill the live browser that the user sees in the drawer.
            import urllib.request as _ureq
            _cdp_alive = False
            try:
                with _ureq.urlopen("http://localhost:9222/json", timeout=2) as _r:
                    _cdp_alive = bool(_r.read())
            except Exception:
                pass

            if not _cdp_alive:
                from python.helpers.app_manager import AppManager
                mgr = AppManager.get_instance()
                app_info = mgr.get_app("shared-browser")
                if app_info:
                    PrintStyle().info("Shared browser CDP not reachable — starting it now...")
                    try:
                        mgr.start_app("shared-browser")
                        # Also open the drawer so the user can see it
                        existing = mgr.get_drawer_state()
                        apps = list(existing.get("apps") or [])
                        if "shared-browser" not in apps:
                            apps.append("shared-browser")
                        mgr.set_drawer_state(open=True, apps=apps, active="shared-browser")
                    except Exception as e:
                        PrintStyle().warning(f"Could not start shared-browser: {e}")

            # Wait for Chromium CDP to be ready before handing off to browser-use
            if not await _wait_for_cdp():
                return Response(
                    message=(
                        "The shared browser CDP endpoint (localhost:9222) is not available. "
                        "The browser may still be starting. Please call open_app with "
                        "app='shared-browser' first, wait a moment, and then try again."
                    ),
                    break_loop=False,
                )

        await self.prepare_state(reset=reset, use_shared=use_shared_bool)
        message = get_secrets_manager(self.agent.context).mask_values(message, placeholder="<secret>{key}</secret>") # mask any potential passwords passed from A0 to browser-use to browser-use format
        task = self.state.start_task(message) if self.state else None

        # wait for browser agent to finish and update progress with timeout
        timeout_seconds = 300  # 5 minute timeout
        start_time = time.time()

        fail_counter = 0
        while not task.is_ready() if task else False:
            # Check for timeout to prevent infinite waiting
            if time.time() - start_time > timeout_seconds:
                PrintStyle().warning(
                    self._mask(f"Browser agent task timeout after {timeout_seconds} seconds, forcing completion")
                )
                break

            await self.agent.handle_intervention()
            await asyncio.sleep(1)
            try:
                if task and task.is_ready():  # otherwise get_update hangs
                    break
                try:
                    update = await asyncio.wait_for(self.get_update(), timeout=10)
                    fail_counter = 0  # reset on success
                except asyncio.TimeoutError:
                    fail_counter += 1
                    PrintStyle().warning(
                        self._mask(f"browser_agent.get_update timed out ({fail_counter}/3)")
                    )
                    if fail_counter >= 3:
                        PrintStyle().warning(
                            self._mask("3 consecutive browser_agent.get_update timeouts, breaking loop")
                        )
                        break
                    continue
                update_log = update.get("log", get_use_agent_log(None))
                self.update_progress("\n".join(update_log))
                screenshot = update.get("screenshot", None)
                if screenshot:
                    self.log.update(screenshot=screenshot)
            except Exception as e:
                PrintStyle().error(self._mask(f"Error getting update: {str(e)}"))

        if task and not task.is_ready():
            PrintStyle().warning(self._mask("browser_agent.get_update timed out, killing the task"))
            self.state.kill_task() if self.state else None
            return Response(
                message=self._mask("Browser agent task timed out, not output provided."),
                break_loop=False,
            )

        # final progress update
        if self.state and self.state.use_agent:
            log_final = get_use_agent_log(self.state.use_agent)
            self.update_progress("\n".join(log_final))

        # collect result with error handling
        try:
            result = await task.result() if task else None
        except Exception as e:
            PrintStyle().error(self._mask(f"Error getting browser agent task result: {str(e)}"))
            # Return a timeout response if task.result() fails
            answer_text = self._mask(f"Browser agent task failed to return result: {str(e)}")
            self.log.update(answer=answer_text)
            return Response(message=answer_text, break_loop=False)
        # finally:
        #     # Stop any further browser access after task completion
        #     # self.state.kill_task()
        #     pass

        # Check if task completed successfully
        if result and result.is_done():
            answer = result.final_result()
            try:
                if answer and isinstance(answer, str) and answer.strip():
                    answer_data = DirtyJson.parse_string(answer)
                    answer_text = strings.dict_to_text(answer_data)  # type: ignore
                else:
                    answer_text = (
                        str(answer) if answer else "Task completed successfully"
                    )
            except Exception as e:
                answer_text = (
                    str(answer)
                    if answer
                    else f"Task completed with parse error: {str(e)}"
                )
        else:
            # Task hit max_steps without calling done()
            urls = result.urls() if result else []
            current_url = urls[-1] if urls else "unknown"
            answer_text = (
                f"Task reached step limit without completion. Last page: {current_url}. "
                f"The browser agent may need clearer instructions on when to finish."
            )

        # Mask answer for logs and response
        answer_text = self._mask(answer_text)

        # update the log (without screenshot path here, user can click)
        self.log.update(answer=answer_text)

        # add screenshot to the answer if we have it
        if (
            self.log.kvps
            and "screenshot" in self.log.kvps
            and self.log.kvps["screenshot"]
        ):
            path = self.log.kvps["screenshot"].split("//", 1)[-1].split("&", 1)[0]
            answer_text += f"\n\nScreenshot: {path}"

        # respond (with screenshot path)
        return Response(message=answer_text, break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(
            type="browser",
            heading=f"icon://captive_portal {self.agent.agent_name}: Calling Browser Agent",
            content="",
            kvps=self.args,
        )

    async def get_update(self):
        result = {}
        agent = self.agent
        ua = self.state.use_agent if self.state else None

        if ua and self.state and self.state.task and not self.state.task.is_ready():
            try:

                async def _get_update():
                    # Build short activity log
                    result["log"] = get_use_agent_log(ua)

                    # Get page and take screenshot entirely inside the DeferredTask's
                    # event loop to avoid cross-event-loop Playwright conflicts.
                    page = await self.state.get_page() if self.state else None
                    if page:
                        path = files.get_abs_path(
                            persist_chat.get_chat_folder_path(agent.context.id),
                            "browser",
                            "screenshots",
                            f"{self.guid}.png",
                        )
                        files.make_dirs(path)
                        await page.screenshot(path=path, full_page=False, timeout=3000)
                        result["screenshot"] = f"img://{path}&t={str(time.time())}"

                await self.state.task.execute_inside(_get_update)

            except Exception:
                pass

        return result

    async def prepare_state(self, reset=False, use_shared=False):
        self.state = self.agent.get_data("_browser_agent_state")
        # Reset if mode changed (shared vs headless) or explicitly requested
        mode_changed = self.state and self.state.use_shared != use_shared
        if (reset or mode_changed) and self.state:
            self.state.kill_task()
        if not self.state or reset or mode_changed:
            self.state = await State.create(self.agent, use_shared=use_shared)
        self.agent.set_data("_browser_agent_state", self.state)

    def update_progress(self, text):
        text = self._mask(text)
        short = text.split("\n")[-1]
        if len(short) > 50:
            short = short[:50] + "..."
        progress = f"Browser: {short}"

        self.log.update(progress=text)
        self.agent.context.log.set_progress(progress)

    def _mask(self, text: str) -> str:
        try:
            return get_secrets_manager(self.agent.context).mask_values(text or "")
        except Exception as e:
            return text or ""

    # def __del__(self):
    #     if self.state:
    #         self.state.kill_task()


def get_use_agent_log(use_agent: browser_use.Agent | None):
    result = ["🚦 Starting task"]
    if use_agent:
        action_results = use_agent.history.action_results() or []
        short_log = []
        for item in action_results:
            # final results
            if item.is_done:
                if item.success:
                    short_log.append("✅ Done")
                else:
                    short_log.append(
                        f"❌ Error: {item.error or item.extracted_content or 'Unknown error'}"
                    )

            # progress messages
            else:
                text = item.extracted_content
                if text:
                    first_line = text.split("\n", 1)[0][:200]
                    short_log.append(first_line)
        result.extend(short_log)
    return result
