# Certificates

The certificates of the company - the CA of a proxy that inspects TLS, the CA of the database - are
put here, each in PEM in a file ending in `.crt`, before the dev container is built: exported from
the certificate manager of Windows as "Base-64 encoded X.509", and renamed from `.cer`, as a file
of another ending is passed over without a word. They are trusted by the system of the container,
by uv, by the tool and by Ollama, and never committed. A certificate added later needs the
container to be rebuilt.
