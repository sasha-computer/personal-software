# Plain Text Running Tracker

## Project Description
In March 2025, I set a goal to run 5k every day for 30 days; 30 days became 100 and to my surprise, even some people close to me also took on the challenge with me once they saw my progress. I was using an Apple Watch Ultra 2 at the time. 2025 also brought a better understanding of my data privacy, and having built a NAS in late 2024, I began self hosting a lot and I tried my best to deshackle myself from unnecessary cloud subscriptions. I ended up switching to a Garmin watch which I mostly use offline (other than with the gadgetbridge app), and so I exported all my Apple health data ready to parse at some point. In classic Apple fashion, the *exported* data was a convoluted
and extremely large XML file. This project allows for parsing of the `export.xml` file provided when exporting your Apple Health data. It also allows for parsing of `*.fit` files from Garmin watches (which unlike Apple, Garmin watches can be plugged into any computer via USB and *shock horror* open up files! that you can do stuff with! nicely named!)

## Environment Setup
- This project uses the excellent [uv](https://docs.astral.sh/uv/) for Python scripting.
- If necessary, please use Python native type hints and/or [ty](https://docs.astral.sh/ty/type-checking/) for type checking.

## Code conventions
- Stick to PEP code conventions.
- 4-space indentation for Python.

## Project Structure
- /apple/ for the `export.xml` file necessary to create/append to `runs.md`
- /garmin/ for the `*.fit` files necessary to create/append to `runs.md`
- /tests/ for pytest tests (`uv run pytest`)

## Important Notes
- Keep Python code as readable as possible. 
- "apex predator of grug is complexity"
- "complexity bad, very very bad"