# ExploitKit (ExpKit) - AD/EDR evasion framework

ExploitKit ([ExpKit](https://gitlab.com/0xCCF4/expkit))
is a framework and build automation tool
to process exploits/payloads to evade antivirus and
endpoint detection response products using reusable
building blocks like encryption or obfuscation stages.

ExpKit automatises the process of modifying exploits/payloads
to evade antivirus and endpoint detection response products by
providing a development/build framework to compile/process
exploit/payload code. Write your evasion processing
stages once and reuse them on your exploit/payloads.
See the [documentation](https://0xccf4.gitlab.io/expkit/api/groups/)
for a list of already included
stages. Those reusable blocks expose parameters
to the user to configure them. Allowing further
customization to prevent detection. A multi-platform (os and architecture)
allows processing exploits/payloads for different
operating systems and architectures.

For the full documentation visit the [docs](https://0xccf4.gitlab.io/expkit/).

Project status: __In development - pre-alpha__

## Features

* Modular design
* Build automation
* Reusable building blocks
* Easy to extend with custom processing stages
* Multi-platform (os and architecture) support
* On-the-fly compilation on web request
* Randomized build output on every build (e.g. random encryption keys)
* Common evasion techniques already (parameterized) implemented (__WIP__)

## Installation

ExpKit can be installed locally using `pip` and `python3.10`,
ideally by using a virtual environment:

```
pip install -e .
```

or by using PyPI:

```
pip install expkit-framework
```

This will install ExpKit and all its runtime dependencies.

## Projects

Projects are configured by a `config.json` file that
includes the definition of the stages to execute and
artifacts (exploits/payloads) to build. The following
code block contains an example configuration for a C#
project: A C# project is loaded from the folder `payload_code`
obfuscated, compiled and exported as `build.exe`.

```json
{
  "config": {
    "BUILD_TYPE": "Release"
  },
  
  "artifacts": {
    "base": {
      "stages": [
        
        {
          "name": "LOAD_FOLDER",
          "config": {
            "LOAD_FOLDER_PATH": "./payload_code",
            "LOAD_TARGET_FORMAT": "CSHARP_PROJECT"
          }
        },
        
        { "name": "OBFUSCATE_CSHARP" },
        
        { "name": "COMPILE_CSHARP" },
        
        {
          "name": "EXPORT",
          "config": {
            "EXPORT_NAME": "build.exe"
          }
        }
        
      ]
    }
  }
}
```

The syntax of the configuration file is described within the
[API Reference](https://0xccf4.gitlab.io/expkit/api/configuration/) section.

## Building a project

To build the project, run the following command:

```bash
expkit build WINDOWS AMD64
```

This will build the project and create an executable file,
according to the configuration, within the current working directory,
named `build.exe`.
Building the project from a different operating system/architecture
requires the setup up of a [build worker](../user-guide/build-worker) environment.

## Serving and building the project on the fly

To serve the project and build a payload on the fly whenever a
web-request is received, run the following command:

```bash
expkit server 80 0.0.0.0 secret-token
```

This will start a web server on port 80 and listen on all interfaces.
The server will build a payload for the operating system and architecture
specified in the web request. The web request must contain the
`secret-token` as a query parameter. The following example shows
a web request to build a payload for Windows 64-bit:

```bash
curl http://localhost:80/build?token=secret-token&os=WINDOWS&arch=AMD64&target=base
```

The `target` parameter specifies the target artifact to build.
When requiring an HTTPS connection, it is advised to run a nginx
proxy in front of the ExpKit server.
