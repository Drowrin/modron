import nox

nox.options.sessions = ['lint', 'typecheck']

INCLUDED = [
    'modron',
    'scripts',
]


@nox.session(reuse_venv=True)
def lint(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", "--check", *INCLUDED)
    session.run("isort", "-c", *INCLUDED)
    session.run("ruff", "check", *INCLUDED)
    session.run("codespell", *INCLUDED)


@nox.session(reuse_venv=True)
def fixes(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", *INCLUDED)
    session.run("isort", *INCLUDED)
    session.run("ruff", "--fix-only", "--exit-zero", *INCLUDED)
    session.run("codespell", "-i", "2", "-w", *INCLUDED)


@nox.session(reuse_venv=True)
def typecheck(session: nox.Session):
    session.install("-r", "requirements/runtime.txt")
    session.install("-r", "requirements/types.txt")

    session.run("pyright", *INCLUDED)
