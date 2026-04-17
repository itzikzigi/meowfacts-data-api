import sys

from meowfacts.cli import already_fetched_today, parse_args
from meowfacts.pipeline import Pipeline
from meowfacts.utils.logger import Logger


def main() -> None:
    args = parse_args()
    Logger.configure(args.verbose)
    logger = Logger(__name__)

    if not args.force and already_fetched_today(args.output):
        logger.info("Output is already up to date for today. Use --force to re-fetch.")
        return

    try:
        pipeline = Pipeline()
        pipeline.run(languages=args.languages, output_path=args.output)
    except Exception as exc:
        logger.critical("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
