"""
a utility to run several commands in parallel
and show the results in order once they're all done
"""

from pathlib import Path
import asyncio

class ParallelSh:

    def __init__(self, commands: list[str], echo=True):
        self.commands = commands
        self.echo = echo

    def run(self):
        """
        a synchronous function that will run all
        subcommands in parallel and show all the results
        sequentially once they're all done
        """
        return asyncio.run(self._run())

    async def _run(self):
        """
        an async function that will run all
        subcommands in parallel and show all the results
        sequentially once they're all done
        """
        tasks = []
        for command in self.commands:
            tasks.append(asyncio.create_task(self._run_command(command)))
        for task in tasks:
            await task

    async def _run_command(self, command):
        """
        an async function that will run a single command
        """
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if self.echo:
            print(f"===> {command}")
        if stdout:
            if stderr:                  # if no stderr, no need to separate
                print("[stdout]:")
            print(stdout.decode(), end="")
        if stderr:
            print("[stderr]:")
            print(stderr.decode(), end="")

if __name__ == "__main__":
    commands = [
        "ls -l",
        "echo the sleeper; sleep 1",        # this one will be the last to finish
        "echo hello",
        "ls -l /tmp",
        """function foo() {
            echo "this is a function"
            [ -f /etc/passwd ] && echo "passwd exists"
        }
        foo
        """
    ]
    ParallelSh(commands).run()
