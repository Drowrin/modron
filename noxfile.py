import nox


@nox.session
def lint(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", "--check", "modron")
    session.run("isort", "-c", "modron")
    session.run("codespell", "modron")


@nox.session
def typecheck(session: nox.Session):
    session.install("-r", "requirements/prod.txt")
    session.install("-r", "requirements/types.txt")
    
    session.run("pyright", "modron")


@nox.session
def fixes(session: nox.Session):
    session.install("-r", "requirements/tools.txt")

    session.run("black", "modron")
    session.run("isort", "modron")
    session.run("codespell", "modron", "-i", "2")
