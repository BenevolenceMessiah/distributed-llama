@echo off
setlocal

:::  ________  _______   ________   _______   ___      ___ ________  ___       _______   ________   ________  _______      
::: |\   __  \|\  ___ \ |\   ___  \|\  ___ \ |\  \    /  /|\   __  \|\  \     |\  ___ \ |\   ___  \|\   ____\|\  ___ \     
::: \ \  \|\ /\ \   __/|\ \  \\ \  \ \   __/|\ \  \  /  / | \  \|\  \ \  \    \ \   __/|\ \  \\ \  \ \  \___|\ \   __/|    
:::  \ \   __  \ \  \_|/_\ \  \\ \  \ \  \_|/_\ \  \/  / / \ \  \\\  \ \  \    \ \  \_|/_\ \  \\ \  \ \  \    \ \  \_|/__  
:::   \ \  \|\  \ \  \_|\ \ \  \\ \  \ \  \_|\ \ \    / /   \ \  \\\  \ \  \____\ \  \_|\ \ \  \\ \  \ \  \____\ \  \_|\ \ 
:::    \ \_______\ \_______\ \__\\ \__\ \_______\ \__/ /     \ \_______\ \_______\ \_______\ \__\\ \__\ \_______\ \_______\
:::     \|_______|\|_______|\|__| \|__|\|_______|\|__|/       \|_______|\|_______|\|_______|\|__| \|__|\|_______|\|_______|
::: 
:::  _____ ______   _______   ________   ________  ___  ________  ___  ___     
::: |\   _ \  _   \|\  ___ \ |\   ____\ |\   ____\|\  \|\   __  \|\  \|\  \    
::: \ \  \\\__\ \  \ \   __/|\ \  \___|_\ \  \___|\ \  \ \  \|\  \ \  \\\  \   
:::  \ \  \\|__| \  \ \  \_|/_\ \_____  \\ \_____  \ \  \ \   __  \ \   __  \  
:::   \ \  \    \ \  \ \  \_|\ \|____|\  \\|____|\  \ \  \ \  \ \  \ \  \ \  \ 
:::    \ \__\    \ \__\ \_______\____\_\  \ ____\_\  \ \__\ \__\ \__\ \__\ \__\
:::     \|__|     \|__|\|_______|\_________\\_________\|__|\|__|\|__|\|__|\|__|
:::                             \|_________\|_________|
::: ___  ________   ________  _________  ________  ___       ___       _______   ________     
::: |\  \|\   ___  \|\   ____\|\___   ___\\   __  \|\  \     |\  \     |\  ___ \ |\   __  \    
::: \ \  \ \  \\ \  \ \  \___|\|___ \  \_\ \  \|\  \ \  \    \ \  \    \ \   __/|\ \  \|\  \   
:::  \ \  \ \  \\ \  \ \_____  \   \ \  \ \ \   __  \ \  \    \ \  \    \ \  \_|/_\ \   _  _\  
:::   \ \  \ \  \\ \  \|____|\  \   \ \  \ \ \  \ \  \ \  \____\ \  \____\ \  \_|\ \ \  \\  \| 
:::    \ \__\ \__\\ \__\____\_\  \   \ \__\ \ \__\ \__\ \_______\ \_______\ \_______\ \__\\ _\ 
:::     \|__|\|__| \|__|\_________\   \|__|  \|__|\|__|\|_______|\|_______|\|_______|\|__|\|__|
:::                    \|_________|

for /f "delims=: tokens=*" %%A in ('findstr /b ::: "%~f0"') do @echo(%%A
:: Play soundbyte from audio
if not exist audio\ mkdir audio
cd audio
set "file=Benevolence_Messiah_DJ_Kwe.wav"
( echo Set Sound = CreateObject("WMPlayer.OCX.7"^)
  echo Sound.URL = "%file%"
  echo Sound.Controls.play
  echo do while Sound.currentmedia.duration = 0
  echo wscript.sleep 100
  echo loop
  echo wscript.sleep (int(Sound.currentmedia.duration^)+1^)*1000) >sound.vbs
start /min sound.vbs
cd ..

timeout /t 3

:: Download the repo code if its not downloaded.
echo As-salamu alaykum!!
echo detecting presence of repo, git cloning if not detected...
echo ---------------------------------------------------------------
if exist tools\ goto Menu1
git clone https://github.com/BenevolenceMessiah/distributed-llama.git
cd distributed-llama
git pull
cd audio
set "file=Benevolence_Messiah_DJ_Kwe.wav"
( echo Set Sound = CreateObject("WMPlayer.OCX.7"^)
  echo Sound.URL = "%file%"
  echo Sound.Controls.play
  echo do while Sound.currentmedia.duration = 0
  echo wscript.sleep 100
  echo loop
  echo wscript.sleep (int(Sound.currentmedia.duration^)+1^)*1000) >sound.vbs
start /min sound.vbs
cd ..
echo ---------------------------------------------------------------

:Menu1
echo ---------------------------------------------------------------
echo Please choose from the following options:
echo - These options are all case sensitive.
echo - Make sure Docker Desktop is up and running on your system!
echo - Press Ctrl+c to exit at any time!
echo ---------------------------------------------------------------
echo 1) Install Distributed Llama.
echo 2) Run Distributed Llama.
echo 3) Install/Launch Distributed Llama for Raspberry Pi cluster.
echo 4) Install Chocolatey (necessary if you don't already have it installed).
echo C) Exit
echo U) Update repo.
echo ---------------------------------------------------------------

set /P option=Enter your choice:
if %option% == 1 goto Install
if %option% == 2 goto Run
if %option% == 3 goto InstallRPi
if %option% == 4 goto Chocolately
if %option% == C goto End
if %option% == U goto Updater

:Install
echo ---------------------------------------------------------------
echo Creating virtual environment
echo ---------------------------------------------------------------
if not exist venv (
    py -3.10 -m venv .venv
) else (
    echo Existing venv detected. Activating.
)
echo Activating virtual environment
call .venv\Scripts\activate
echo --------------------------------------------------------------
python.exe -m pip install --upgrade pip
call choco install mingw
call make dllama
call make dllama-api
echo Installation complete!
echo --------------------------------------------------------------
timeout /t -1
goto Menu1

:Run
echo ---------------------------------------------------------------
echo Firing up the server...
echo And
echo Firing up the CLI!
echo ---------------------------------------------------------------
if not exist venv (
    py -3.10 -m venv .venv
) else (
    echo Existing venv detected. Activating.
)
echo Activating virtual environment
call .venv\Scripts\activate
echo ---------------------------------------------------------------
call ollama pull mistral
start call ollama serve
call litellm --model ollama/mistral
call export OPENAI_API_BASE="http://localhost:8000"
start call gptme --help
start call gptme-server -v
start start http://localhost:5000/
start call docker run
goto Menu1

:Configure
echo Opening Configuration File...
echo This file will not exist until first run.
echo ---------------------------------------------------------------
timeout /t -1
start call config.toml
goto Menu1

:DockerDesktop
echo Installing Docker Desktop
echo ---------------------------------------------------------------
cd /d %~dp0
call curl "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe?utm_source=docker&utm_medium=webreferral&utm_campaign=dd-smartbutton&utm_location=module" -o docker-desktop-installer.exe
start call docker-desktop-installer.exe
echo Once the install is complete, continue.
echo ---------------------------------------------------------------
timeout /t -1
echo Restarting...
echo Deleting installer .exe file if it exists...
echo ---------------------------------------------------------------
if exist docker-desktop-installer.exe del docker-desktop-installer.exe
start call Run_gptme.bat
exit

:Updater
echo ---------------------------------------------------------------
echo Updating repo...
echo ---------------------------------------------------------------
ls | xargs -I{} git -C {} pull
echo Complete!
echo ---------------------------------------------------------------
goto Menu1

:End 
echo ---------------------------------------------------------------
echo As-salamu alaykum!!
echo ---------------------------------------------------------------
pause