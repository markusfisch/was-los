# Contribution Guidelines

Please try to keep things in good shape and comply to what's there.

This code is formatted according to [PEP8][pep8] and there's a `format` rule
in the `Makefile` to apply [PEP8][pep8] to all source files:

	$ make format

When adding new features use the [topic branch workflow][topic_branch] and
make sure to [squash][squash] when merging into master:

	$ git merge cool_feature --squash

Then take your time and write a [good commit messages][commit_messages]
to keep the history meaningful and useful. One feature, one commit.

[pep8]: https://www.python.org/dev/peps/pep-0008/
[topic_branch]: https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows#_topic_branch
[squash]: https://git-scm.com/docs/git-stash
[commit_messages]: https://juffalow.com/other/write-good-git-commit-message
