import sass

def compile_scss():
    sass.compile(dirname=('app/static/sass/', 'app/static/css/'))

if __name__ == "__main__":
    compile_scss()
