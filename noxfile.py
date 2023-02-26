import nox

INCLUDED = [
    'modron',
    'scripts',
]


@nox.session
def lint(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", "--check", *INCLUDED)
    session.run("isort", "-c", *INCLUDED)
    session.run("ruff", "check", *INCLUDED)
    session.run("codespell", *INCLUDED)


@nox.session
def fixes(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", *INCLUDED)
    session.run("isort", *INCLUDED)
    session.run("ruff", "--fix-only", *INCLUDED)
    session.run("codespell", "-i", "2", "-w", *INCLUDED)


@nox.session
def typecheck(session: nox.Session):
    session.install("-r", "requirements/prod.txt")
    session.install("-r", "requirements/types.txt")
    
    session.run("pyright", *INCLUDED)
