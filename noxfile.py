import nox

@nox.session
def lint(session: nox.Session):
    session.install("poetry")
    session.run("poetry", "install")
    
    session.run("black", "--check", "modron")
    session.run("codespell", "modron")
    session.run("mypy", "modron")
    

@nox.session
def fixes(session: nox.Session):
    session.install("poetry")
    session.run("poetry", "install")
    
    session.run("isort", "modron")
    session.run("black", "modron")
    session.run("codespell", "modron", "-i", "2")
