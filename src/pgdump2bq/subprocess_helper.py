import asyncio
import logging
import subprocess

logger = logging.getLogger(__name__)


def run_command(cmd):
    """Run command in subprocess, raise exception if process has error."""
    logger.debug(f"Running command: {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        logger.exception(f"Error running command: {cmd}, returncode: {e.returncode}")
        logger.error(f"Stdout: {e.stdout}")
        logger.error(f"Stderr: {e.stderr}")
        raise
    else:
        logger.debug(f"Stdout: {result.stdout}")
        logger.debug(f"Stderr: {result.stderr}")
        return result


def run_command_async(cmd):
    """Run command asynchronously, returning object that can be used to ctrl+c the process later"""
    logger.debug(f"Running command asynchronously: {cmd}")
    return subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


async def run_command_async_await(cmd):
    """Run command asynchronously using asyncio, raise exception if process has error."""
    logger.debug(f"Running async command: {cmd}")
    try:
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Error running command: {cmd}, returncode: {process.returncode}")
            logger.error(f"Stdout: {stdout.decode()}")
            logger.error(f"Stderr: {stderr.decode()}")
            raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
        
        logger.debug(f"Stdout: {stdout.decode()}")
        logger.debug(f"Stderr: {stderr.decode()}")
        return process.returncode, stdout, stderr
        
    except Exception as e:
        logger.exception(f"Error running async command: {cmd}")
        raise
