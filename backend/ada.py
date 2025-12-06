import asyncio
import base64
import io
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import pyaudio
import PIL.Image
import mss
from google.genai import types

import argparse

from google import genai

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup

    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from tools import tools_list

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025"

DEFAULT_MODE = "camera"

load_dotenv()
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))

# Function definitions
generate_cad = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

run_web_agent = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

tools = [{'google_search': {}}, {"function_declarations": [generate_cad, run_web_agent]}]
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    system_instruction="You are a helpful assistant named Ada and answer in a friendly tone.",
    tools=tools,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Kore"
            )
        )
    )
)

pya = pyaudio.PyAudio()

from cad_agent import CadAgent
from web_agent import WebAgent

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, input_device_index=None, output_device_index=None):
        self.video_mode = video_mode
        self.on_audio_data = on_audio_data
        self.on_video_frame = on_video_frame
        self.on_cad_data = on_cad_data
        self.on_web_data = on_web_data
        self.input_device_index = input_device_index
        self.output_device_index = output_device_index

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.session = None
        
        self.cad_agent = CadAgent()
        self.web_agent = WebAgent()

        self.send_text_task = None
        self.stop_event = asyncio.Event()

    def set_paused(self, paused):
        self.paused = paused

    def stop(self):
        self.stop_event.set()

    async def send_frame(self, frame_data):
        if not self.out_queue:
            return
        # frame_data is mostly likely bytes from the frontend blob
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode('utf-8')
        else:
            b64_data = frame_data # Assume string/b64 already if not bytes
            
        await self.out_queue.put({"mime_type": "image/jpeg", "data": b64_data})

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg, end_of_turn=False)
            # await self.session.send_realtime_input(inputs=[msg])

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=self.input_device_index if self.input_device_index is not None else mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                if self.out_queue:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            except Exception as e:
                print(f"Error reading audio: {e}")
                await asyncio.sleep(0.1)

    async def handle_cad_request(self, prompt):
        print(f"[ADA DEBUG] 🧵 Background Task Started: handle_cad_request('{prompt}')")
        # Call the secondary agent
        cad_data = await self.cad_agent.generate_prototype(prompt)
        
        if cad_data:
            print(f"[ADA DEBUG] ✅ CadAgent returned data successfully.")
            print(f"[ADA DEBUG] 📊 Data Check: {len(cad_data.get('vertices', []))} vertices, {len(cad_data.get('edges', []))} edges.")
            
            if self.on_cad_data:
                print(f"[ADA DEBUG] 📡 Dispatching data to frontend callback...")
                self.on_cad_data(cad_data)
                print(f"[ADA DEBUG] 📨 Dispatch complete.")
            
            # Notify the model that the task is done, so it can tell the user
            # We send this as a "User" message to prompt the model to speak
            completion_msg = "System Notification: CAD generation is complete. Inform the user that the model is ready."
            try:
                await self.session.send(input=completion_msg, end_of_turn=True)
                print(f"[ADA DEBUG] 🔔 Sent completion notification to model.")
            except Exception as e:
                 print(f"[ADA DEBUG] ❌ Failed to send completion notification: {e}")

        else:
            print(f"[ADA DEBUG] ❌ CadAgent returned None.")
            # Optionally notify failure
            try:
                await self.session.send(input="System Notification: CAD generation failed.", end_of_turn=True)
            except Exception:
                pass

    async def handle_web_agent_request(self, prompt):
        print(f"[ADA DEBUG] 🌐 Web Agent Task: '{prompt}'")
        
        async def update_frontend(image_b64, log_text):
            # Send screenshot to frontend via socket (handled by server.py usually, but here we push to out_queue for generic handling or need direct socket access)
            # Since AudioLoop sends to out_queue which goes to 'session.send', that's for the MODEL.
            # To send to FRONTEND, we need to use the method server.py uses. 
            # In this architecture, AudioLoop doesn't have direct access to the flask-socketio instance unless passed or via a callback.
            # However, looking at logic, 'on_cad_data' was passed. We should probably accept 'on_browser_data' too.
            # For now, let's assume we can trigger an event or reuse a callback.
            
            if self.on_web_data:
                 self.on_web_data({"image": image_b64, "log": log_text})
                 
        await self.web_agent.run_task(prompt, update_callback=update_frontend)
        print("[ADA DEBUG] 🌐 Web Agent Task Complete")

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        continue
                    
                    if response.tool_call:
                        print("The tool was called")
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            if fc.name == "generate_cad":
                                prompt = fc.args["prompt"]
                                print(f"\n[ADA DEBUG] --------------------------------------------------")
                                print(f"[ADA DEBUG] 🛠️ Tool Call Detected: 'generate_cad'")
                                print(f"[ADA DEBUG] 📥 Arguments: prompt='{prompt}'")
                                print(f"[ADA DEBUG] 🚀 Spawning CadAgent.generate_prototype() in background...")

                                # Fire and forget (task will notify when done)
                                asyncio.create_task(self.handle_cad_request(prompt))
                                
                                result_text = "CAD calibration started. The model is being generated in the background."
                                function_response = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={
                                        "result": result_text,
                                        "scheduling": "INTERRUPT"
                                    }
                                )
                                function_responses.append(function_response)

                            elif fc.name == "run_web_agent":
                                prompt = fc.args["prompt"]
                                print(f"[ADA DEBUG] 🛠️ Tool Call: 'run_web_agent' with prompt='{prompt}'")
                                asyncio.create_task(self.handle_web_agent_request(prompt))
                                
                                result_text = "Web Navigation started. Browser window opened."
                                function_response = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={
                                        "result": result_text,
                                        "scheduling": "INTERRUPT"
                                    }
                                )
                                function_responses.append(function_response)

                        await self.session.send_tool_response(function_responses=function_responses)

                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
        except Exception as e:
            print(f"Error in receive_audio: {e}")

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            output_device_index=self.output_device_index,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            if self.on_audio_data:
                self.on_audio_data(bytestream)
            await asyncio.to_thread(stream.write, bytestream)

    async def get_frames(self):
        # Placeholder if camera mode is handled by frontend sending frames, 
        # but if this mode is 'camera' AND we want backend to grab frames (unlikely with frontend video feed),
        # we can implement it. 
        # However, Ada v2 architecture seems to rely on frontend sending frames for 'camera'.
        # But 'server.py' sets video_mode="none" by default!
        # If video_mode is "none", this task isn't started (logic in run()).
        # server.py calls send_frame explicitly.
        # So we don't strictly need this unless running standalone.
        # I'll include the basic version from test.py just in case.
        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            if self.out_queue:
                await self.out_queue.put(frame)
        cap.release()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def _get_screen(self):
        # Not fully needed given server.py logic but good for completeness
        pass 
    async def get_screen(self):
         pass

    async def run(self):
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())

                if self.video_mode == "camera":
                    tg.create_task(self.get_frames())
                elif self.video_mode == "screen":
                    tg.create_task(self.get_screen())

                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())

                await self.stop_event.wait()

        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream.close()
            traceback.print_exception(EG)
        except Exception as e:
            print(f"Run error: {e}")
            if hasattr(self, 'audio_stream') and self.audio_stream:
                self.audio_stream.close()

def get_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

def get_output_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())