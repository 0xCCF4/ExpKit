# Getting started

ExploitKit ([ExpKit](https://gitlab.com/0xCCF4/expkit))
is a framework and build automation tool
to process exploits/payloads to evade antivirus and
endpoint detection response products using reusable
building blocks like encryption or obfuscation stages.

## Installation

ExpKit can be installed locally using `pip` and `python3.10`,
ideally by using a virtual environment:

=== "PyPI"

    ```bash
    pip install expkit-framework
    ```

=== "Local"

    ```bash
    pip install -e .
    ```

=== "Local development"

    ```bash
    pip install -e .[dev]
    ```

This will install ExpKit and all its runtime dependencies.

## Creating a new project

Create a new folder containing a `config.json` file and
your exploit/payload code. The `config.json` contains
the configuration for the project. The following example
shows an example configuration for a C# project assuming
the C# project is located in a sub folder named `payload_code`:

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
[API Reference](../api/configuration) section.

## Building the project

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
