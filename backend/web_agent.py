import os
import time
import asyncio
import base64
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from google import genai
from google.genai import types

# 1. Load API Key
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("Please set GEMINI_API_KEY in your .env file")

# 2. Configuration
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900
# UPDATED: Use the specific Computer Use preview model
MODEL_ID = "gemini-2.5-computer-use-preview-10-2025"

class WebAgent:
    def __init__(self):
        self.client = genai.Client(api_key=API_KEY)
        self.browser = None
        self.context = None
        self.page = None

    def denormalize_x(self, x: int, width: int) -> int:
        return int((x / 1000) * width)

    def denormalize_y(self, y: int, height: int) -> int:
        return int((y / 1000) * height)

    async def execute_function_calls(self, function_calls):
        results = []
        
        for call in function_calls:
            # Extract ID if available, otherwise it might be None or empty depending on the SDK version
            # But the Computer Use model typically expects IDs to be threaded back.
            call_id = getattr(call, 'id', None)
            fn_name = call.name
            args = call.args
            print(f"🤖 Action: {fn_name} {args}")

            # --- SAFETY CHECK ---
            requires_acknowledgement = False
            if "safety_decision" in args:
                 decision = args["safety_decision"]
                 if decision.get("decision") == "require_confirmation":
                     print(f"   🛡️ Safety Alert: {decision.get('explanation')}")
                     print("   -> Auto-acknowledging to proceed.")
                     requires_acknowledgement = True

            result_data = {}
            
            try:
                # --- NAVIGATION ---
                if fn_name == "open_web_browser":
                    pass 
                elif fn_name == "navigate":
                    await self.page.goto(args["url"])
                elif fn_name == "go_back":
                    await self.page.go_back()
                elif fn_name == "go_forward":
                    await self.page.go_forward()
                elif fn_name == "search":
                    await self.page.goto("https://www.google.com")
                elif fn_name == "wait_5_seconds":
                    await asyncio.sleep(5)

                # --- MOUSE CLICKS & TYPING ---
                elif fn_name == "click_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.click(x, y)
                    
                elif fn_name == "type_text_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    text = args["text"]
                    press_enter = args.get("press_enter", False)
                    clear_before = args.get("clear_before_typing", True)
                    
                    await self.page.mouse.click(x, y)
                    if clear_before:
                        # 'Meta+A' for Mac, 'Control+A' for Windows/Linux
                        # Simply using Control+A is usually fine for headless linux/windows envs
                        await self.page.keyboard.press("Control+A") 
                        await self.page.keyboard.press("Backspace")
                    
                    await self.page.keyboard.type(text)
                    if press_enter:
                        await self.page.keyboard.press("Enter")

                # --- MOUSE MOVEMENT / HOVER ---
                elif fn_name == "hover_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.move(x, y)

                elif fn_name == "drag_and_drop":
                    start_x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    start_y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    end_x = self.denormalize_x(args["destination_x"], SCREEN_WIDTH)
                    end_y = self.denormalize_y(args["destination_y"], SCREEN_HEIGHT)
                    
                    await self.page.mouse.move(start_x, start_y)
                    await self.page.mouse.down()
                    await self.page.mouse.move(end_x, end_y)
                    await self.page.mouse.up()

                # --- KEYBOARD ---
                elif fn_name == "key_combination":
                    key_comb = args.get("keys")
                    await self.page.keyboard.press(key_comb)

                # --- SCROLLING ---
                elif fn_name == "scroll_document" or fn_name == "scroll_at":
                    magnitude = args.get("magnitude", 800)
                    direction = args.get("direction", "down")
                    
                    # If scroll_at, move mouse there first
                    if fn_name == "scroll_at":
                        x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                        y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                        await self.page.mouse.move(x, y)

                    dx, dy = 0, 0
                    if direction == "down": dy = magnitude
                    elif direction == "up": dy = -magnitude
                    elif direction == "right": dx = magnitude
                    elif direction == "left": dx = -magnitude
                    
                    await self.page.mouse.wheel(dx, dy)

                else:
                    print(f"⚠️ Warning: Model requested unimplemented function {fn_name}")

                # Wait a moment for UI to settle
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Error executing {fn_name}: {e}")
                result_data = {"error": str(e)}

            # Add the acknowledgement flag if needed
            if requires_acknowledgement:
                result_data["safety_acknowledgement"] = True

            results.append((call_id, fn_name, result_data))
        
        return results

    async def get_function_responses(self, results):
        # UPDATED: Changed "jpeg" to "png" to satisfy Computer Use model requirements
        screenshot_bytes = await self.page.screenshot(type="png") 
        current_url = self.page.url
        
        function_responses = []
        for call_id, name, result in results:
            response_data = {"url": current_url}
            response_data.update(result)
            
            # Construct the response object
            # Note: The SDK might change how 'id' is passed. 
            # If 'types.FunctionResponse' supports 'id', we pass it.
            # Based on standard Google GenAI SDK usage for function calling:
            function_responses.append(
                types.FunctionResponse(
                    name=name,
                    id=call_id, # critical for matching request-response
                    response=response_data,
                    parts=[types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            # UPDATED: Changed "image/jpeg" to "image/png"
                            mime_type="image/png",
                            data=screenshot_bytes
                        )
                    )]
                )
            )
        return function_responses, screenshot_bytes

    async def run_task(self, prompt, update_callback=None):
        """
        Runs the agent with the given prompt.
        update_callback: async function(screenshot_b64: str, logs: str)
        Returns the final response from the agent.
        """
        print(f"✨ WebAgent started. Goal: {prompt}")
        final_response = "Agent finished without a final summary."

        async with async_playwright() as p:
            # Launch browser (Headless=True usually, but for dev we might keep it hidden)
            # Use headless=True for server deployment
            self.browser = await p.chromium.launch(headless=True) 
            self.context = await self.browser.new_context(
                viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            
            # Start at Google
            await self.page.goto("https://www.google.com")

            config = types.GenerateContentConfig(
                tools=[types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER
                    )
                )],
                thinking_config=types.ThinkingConfig(include_thoughts=True) 
            )

            # UPDATED: Capture initial screenshot as PNG
            initial_screenshot = await self.page.screenshot(type="png")
            
            # Send initial state
            if update_callback:
                encoded_image = base64.b64encode(initial_screenshot).decode('utf-8')
                await update_callback(encoded_image, "Web Agent Initialized")

            chat_history = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        # UPDATED: Use PNG mime type
                        types.Part.from_bytes(data=initial_screenshot, mime_type="image/png")
                    ]
                )
            ]

            MAX_TURNS = 20
            
            for turn in range(MAX_TURNS):
                print(f"\n--- Turn {turn + 1} ---")
                
                try:
                    response = await self.client.aio.models.generate_content(
                        model=MODEL_ID,
                        contents=chat_history,
                        config=config
                    )
                except Exception as e:
                    print(f"🔥 Critical API Error: {e}")
                    if update_callback: await update_callback(None, f"Error: {e}")
                    break
                
                # Check for empty response
                if not response.candidates:
                    print("⚠️ Model returned no content.")
                    break
                
                candidate = response.candidates[0]
                model_content = candidate.content
                chat_history.append(model_content)

                # Process thoughts and tool calls
                has_tool_use = False
                thought_text = ""
                agent_text = ""
                
                for part in model_content.parts:
                    if part.thought:
                        print(f"🧠 Thought: {part.text}")
                        thought_text += f"[Thoughts] {part.text}\n"
                    elif part.text:
                        print(f"🗣️ Agent: {part.text}")
                        thought_text += f"[Agent] {part.text}\n"
                        agent_text = part.text
                    if part.function_call:
                        has_tool_use = True
                
                if agent_text:
                    final_response = agent_text

                if update_callback and thought_text:
                     # Send thoughts without image update yet
                     pass # await update_callback(None, thought_text)

                function_calls = [part.function_call for part in model_content.parts if part.function_call]
                
                if not function_calls:
                    if not has_tool_use:
                        print("✅ Task finished details.")
                        if update_callback: await update_callback(None, "Task Finished")
                        break
                    else:
                        print("...Thinking...")
                        continue

                # Execute Actions
                results = await self.execute_function_calls(function_calls)
                
                # Capture new state
                print("📸 Capturing new state...")
                function_responses, screenshot_bytes = await self.get_function_responses(results)
                
                # Update frontend
                if update_callback:
                    encoded_image = base64.b64encode(screenshot_bytes).decode('utf-8')
                    # Format a log message from the actions taken
                    actions_log = ", ".join([r[1] for r in results])
                    await update_callback(encoded_image, f"Executed: {actions_log}")

                # Send Response Back
                response_parts = [types.Part(function_response=fr) for fr in function_responses]
                chat_history.append(types.Content(role="user", parts=response_parts))

            await self.browser.close()
            print("🔒 Browser closed.")
            return final_response

if __name__ == "__main__":
    agent = WebAgent()
    asyncio.run(agent.run_task("Go to google.com and search for 'Gemini API' pricing."))