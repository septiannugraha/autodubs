import streamlit as st
import whisper
from pytube import YouTube
from pydub import AudioSegment
import pandas as pd
import io
import os
import subprocess
import anthropic
from elevenlabs import generate, set_api_key
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

def combine_video(video_filename):
    ffmpeg_extract_subclip(video_filename, 0, 60, targetname="cut_video.mp4")
    output_filename = "output.mp4"
    command = ["ffmpeg", "-y", "-i", "cut_video.mp4", "-i", "output.mp3", "-c:v", "copy", "-c:a", "aac", output_filename]
    subprocess.run(command)
    return output_filename

def shorten_audio(filename):
    filename = "cut_audio.mp4"
    audio = AudioSegment.from_file(filename)
    cut_audio = audio[:60 * 1000]
    cut_audio.export(filename, format="mp4")
    return filename

def generate_translation(original_text, destination_language):
    prompt = (f"{anthropic.HUMAN_PROMPT} Please translate this video transcript into {destination_language}. You will get to the translation directly after I prompted 'the translation:'"
              f"{anthropic.AI_PROMPT} Understood, I will get to the translation without any opening lines."
              f"{anthropic.HUMAN_PROMPT} Great! this is the transcript: {original_text}; the translation:")

    c = anthropic.Anthropic(api_key=st.secrets["claude_key"])
    resp = c.completions.create(
        prompt=f"{prompt} {anthropic.AI_PROMPT}",
        stop_sequences=[anthropic.HUMAN_PROMPT],
        model="claude-v1.3-100k",
        max_tokens_to_sample=900,
    )

    print(resp.completion)
    return resp.completion

def generate_dubs(text):
    # main_audio = AudioSegment.silent(duration=int(60 * 1000))

    set_api_key(st.secrets['xi_api_key'])
    audio = generate(
                    text=text,
                    voice="Bella",
                    model='eleven_multilingual_v1'
                )

    audio_io = io.BytesIO(audio)
    insert_audio = AudioSegment.from_file(audio_io, format='mp3')
    # for i, row in df.iterrows():
    #     set_api_key(st.secrets['xi_api_key'])
    #     audio = generate(
    #                     text=row['text'],
    #                     voice="Bella",
    #                     model='eleven_monolingual_v1'
    #                 )

    #     audio_io = io.BytesIO(audio)

    #                 # Load the TTS audio
    #     insert_audio = AudioSegment.from_file(audio_io, format='mp3')

    #                 # Calculate the start and end times in milliseconds
    #     start_time = int(row['start'] * 1000)
    #     end_time = int(row['end'] * 1000)

    #                 # Insert the TTS audio into the main audio
    #     main_audio = main_audio[:start_time] + insert_audio + main_audio[end_time:]
    return insert_audio
st.title("AutoDubs 📺🎵")

link = st.text_input("Link to Youtube Video", key="link")


language = st.selectbox("Translate to", ("French", "German", "Hindi", "Italian", "Polish", "Portuguese", "Spanish"))

if st.button("Transcribe!"):
    print(f"downloading from link: {link}")
    model = whisper.load_model("base")
    yt = YouTube(link)

    if yt is not None:
        st.subheader(yt.title)
        st.image(yt.thumbnail_url)
        audio_name = st.caption("Downloading audio stream...")
        audio_streams = yt.streams.filter(only_audio=True)
        filename = audio_streams.first().download()
        if filename:
            audio_name.caption(filename)
            cut_audio = shorten_audio(filename)
            transcription = model.transcribe(cut_audio)
            print(transcription)
            if transcription:
                df = pd.DataFrame(transcription['segments'], columns=['start', 'end', 'text'])
                st.dataframe(df)

                dubbing_caption = st.caption("Begin dubbing...")
                # main_audio = generate_dubs(df)
                translation = generate_translation(transcription['text'], language)
                main_audio = generate_dubs(translation)

                main_audio.export("output.mp3", format="mp3")
                dubbing_caption.caption("Dubs generated! combining with the video...")
                video_streams = yt.streams.filter(only_video=True)
                video_filename = video_streams.first().download()

                if video_filename:
                    dubbing_caption.caption("Video downloaded! combining the video and the dubs...")
                    output_filename = combine_video(video_filename)
                    if os.path.exists(output_filename):
                        dubbing_caption.caption("Video successfully dubbed! Enjoy! 😀")
                        st.video(output_filename)
