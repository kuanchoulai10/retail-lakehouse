from configs import JobSettings
from sql_builder import IcebergCallBuilder


def main():
    settings = JobSettings()  # ty: ignore[missing-argument]
    print(IcebergCallBuilder(settings).build_sql())


if __name__ == "__main__":
    main()
