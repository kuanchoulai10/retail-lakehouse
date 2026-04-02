from configs import JobSettings


def main():
    settings = JobSettings()
    print(settings.model_dump())


if __name__ == "__main__":
    main()
