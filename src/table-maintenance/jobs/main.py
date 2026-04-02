from configs import JobSettings
from sql_builder import IcebergCallBuilder


def main():
    settings = JobSettings()
    print(IcebergCallBuilder(settings).build_sql())


if __name__ == "__main__":
    main()
