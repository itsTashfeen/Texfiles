"""Overleaf Two-Way Sync Tool"""
##################################################
# MIT License
##################################################
# File: olsync.py
# Description: Overleaf Two-Way Sync
# Author: Moritz Glöckl
# License: MIT
# Version: 1.2.0
##################################################

import click
import os
import stat
from yaspin import yaspin
import pickle
import zipfile
import io
import dateutil.parser
import glob
import fnmatch
import traceback
from pathlib import Path

try:
    # Import for pip installation / wheel
    from olsync.olclient import OverleafClient
    import olsync.olbrowserlogin as olbrowserlogin
except ImportError:
    # Import for development
    from olclient import OverleafClient
    import olbrowserlogin


@click.group(invoke_without_command=True)
@click.option('-l', '--local-only', 'local', is_flag=True, help="Sync local project files to Overleaf only.")
@click.option('-r', '--remote-only', 'remote', is_flag=True,
              help="Sync remote project files from Overleaf to local file system only.")
@click.option('-n', '--name', 'project_name', default="",
              help="Specify the Overleaf project name instead of the default name of the sync directory.")
@click.option('--store-path', 'cookie_path', default=".olauth", type=click.Path(exists=False),
              help="Relative path to load the persisted Overleaf cookie.")
@click.option('-p', '--path', 'sync_path', default=".", type=click.Path(exists=True),
              help="Path of the project to sync.")
@click.option('-i', '--olignore', 'olignore_path', default=".olignore", type=click.Path(exists=False),
              help="Path to the .olignore file relative to sync path (ignored if syncing from remote to local). See "
                   "fnmatch / unix filename pattern matching for information on how to use it.")
@click.option('--clean-remote', 'clean_remote', is_flag=True,
              help="Delete files matching .olignore from Overleaf (asks once), then exit without syncing.")
@click.option('-v', '--verbose', 'verbose', is_flag=True, help="Enable extended error logging.")
@click.version_option(package_name='overleaf-sync')
@click.pass_context
def main(ctx, local, remote, project_name, cookie_path, sync_path, olignore_path, clean_remote, verbose):
    if ctx.invoked_subcommand is None:
        if not os.path.isfile(cookie_path):
            raise click.ClickException(
                "Persisted Overleaf cookie not found. Please login or check store path.")

        with open(cookie_path, 'rb') as f:
            store = pickle.load(f)

        overleaf_client = OverleafClient(store["cookie"], store["csrf"])

        # Change the current directory to the specified sync path
        os.chdir(sync_path)

        project_name = project_name or os.path.basename(os.getcwd())
        project = execute_action(
            lambda: overleaf_client.get_project(project_name),
            "Querying project",
            "Project queried successfully.",
            "Project could not be queried.",
            verbose)

        project_infos = execute_action(
            lambda: overleaf_client.get_project_infos(project["id"]),
            "Querying project details",
            "Project details queried successfully.",
            "Project details could not be queried.",
            verbose)

        if clean_remote:
            clean_remote_files(overleaf_client, project["id"], project_infos, load_olignore(olignore_path), verbose)
            return

        zip_file = execute_action(
            lambda: zipfile.ZipFile(io.BytesIO(
                overleaf_client.download_project(project["id"]))),
            "Downloading project",
            "Project downloaded successfully.",
            "Project could not be downloaded.",
            verbose)

        sync = not (local or remote)

        ignore_patterns = load_olignore(olignore_path)
        remote_files = [name for name in zip_file.namelist()
                        if not name.endswith('/') and not is_ignored(name, ignore_patterns)]
        local_files = olignore_keep_list(olignore_path)
        remote_set = set(remote_files)
        local_set = set(local_files)
        errors = []

        if remote or sync:
            errors += sync_func(
                files_from=remote_files,
                deleted_files=[f for f in local_files if f not in remote_set and not sync],
                create_file_at_to=lambda name: write_file(name, zip_file.read(name)),
                delete_file_at_to=lambda name: delete_local_file(name),
                create_file_at_from=lambda name: overleaf_client.upload_file(
                    project["id"], project_infos, name, os.path.getsize(name), open(name, 'rb')),
                from_exists_in_to=lambda name: os.path.isfile(name),
                from_equal_to_to=lambda name: open(name, 'rb').read() == zip_file.read(name),
                from_newer_than_to=lambda name: dateutil.parser.isoparse(project["lastUpdated"]).timestamp() >
                                                os.path.getmtime(name),
                from_name="remote",
                to_name="local",
                verbose=verbose)
        if local or sync:
            errors += sync_func(
                files_from=local_files,
                deleted_files=[f for f in remote_files if f not in local_set and not sync],
                create_file_at_to=lambda name: overleaf_client.upload_file(
                    project["id"], project_infos, name, os.path.getsize(name), open(name, 'rb')),
                delete_file_at_to=lambda name: overleaf_client.delete_file(project["id"], project_infos, name),
                create_file_at_from=lambda name: write_file(name, zip_file.read(name)),
                from_exists_in_to=lambda name: name in zip_file.namelist(),
                from_equal_to_to=lambda name: open(name, 'rb').read() == zip_file.read(name),
                from_newer_than_to=lambda name: os.path.getmtime(name) > dateutil.parser.isoparse(
                    project["lastUpdated"]).timestamp(),
                from_name="local",
                to_name="remote",
                verbose=verbose)
            errors += push_empty_folders(overleaf_client, project["id"], project_infos, ignore_patterns, verbose)

        if errors:
            raise click.ClickException(
                "\n[ERROR] %d file(s) failed to sync:\n\t%s" % (len(errors), "\n\t".join(errors)))


@main.command()
@click.option('--path', 'cookie_path', default=".olauth", type=click.Path(exists=False),
              help="Path to store the persisted Overleaf cookie.")
@click.option('-v', '--verbose', 'verbose', is_flag=True, help="Enable extended error logging.")
def login(cookie_path, verbose):
    if os.path.isfile(cookie_path) and not click.confirm(
            'Persisted Overleaf cookie already exist. Do you want to override it?'):
        return
    click.clear()
    execute_action(lambda: login_handler(cookie_path), "Login",
                   "Login successful. Cookie persisted as `" + click.format_filename(
                       cookie_path) + "`. You may now sync your project.",
                   "Login failed. Please try again.", verbose)


@main.command(name='list')
@click.option('--store-path', 'cookie_path', default=".olauth", type=click.Path(exists=False),
              help="Relative path to load the persisted Overleaf cookie.")
@click.option('-v', '--verbose', 'verbose', is_flag=True, help="Enable extended error logging.")
def list_projects(cookie_path, verbose):
    def query_projects():
        for index, p in enumerate(sorted(overleaf_client.all_projects(), key=lambda x: x['lastUpdated'], reverse=True)):
            if not index:
                click.echo("\n")
            click.echo(f"{dateutil.parser.isoparse(p['lastUpdated']).strftime('%m/%d/%Y, %H:%M:%S')} - {p['name']}")
        return True

    if not os.path.isfile(cookie_path):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path.")

    with open(cookie_path, 'rb') as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    click.clear()
    execute_action(query_projects, "Querying all projects",
                   "Querying all projects successful.",
                   "Querying all projects failed. Please try again.", verbose)


@main.command(name='download')
@click.option('-n', '--name', 'project_name', default="",
              help="Specify the Overleaf project name instead of the default name of the sync directory.")
@click.option('--download-path', 'download_path', default=".", type=click.Path(exists=True))
@click.option('--store-path', 'cookie_path', default=".olauth", type=click.Path(exists=False),
              help="Relative path to load the persisted Overleaf cookie.")
@click.option('-v', '--verbose', 'verbose', is_flag=True, help="Enable extended error logging.")
def download_pdf(project_name, download_path, cookie_path, verbose):
    def download_project_pdf():
        nonlocal project_name
        project_name = project_name or os.path.basename(os.getcwd())
        project = execute_action(
            lambda: overleaf_client.get_project(project_name),
            "Querying project",
            "Project queried successfully.",
            "Project could not be queried.",
            verbose)

        file_name, content = overleaf_client.download_pdf(project["id"])

        if file_name and content:
            # Change the current directory to the specified sync path
            os.chdir(download_path)
            open(file_name, 'wb').write(content)

        return True

    if not os.path.isfile(cookie_path):
        raise click.ClickException(
            "Persisted Overleaf cookie not found. Please login or check store path.")

    with open(cookie_path, 'rb') as f:
        store = pickle.load(f)

    overleaf_client = OverleafClient(store["cookie"], store["csrf"])

    click.clear()

    execute_action(download_project_pdf, "Downloading project's PDF",
                   "Downloading project's PDF successful.",
                   "Downloading project's PDF failed. Please try again.", verbose)


def login_handler(path):
    store = olbrowserlogin.login()
    if store is None:
        return False
    with open(path, 'wb+') as f:
        pickle.dump(store, f)
    return True


def delete_file(path):
    _dir = os.path.dirname(path)
    if _dir == path:
        return

    if _dir != '' and not os.path.exists(_dir):
        return
    else:
        os.remove(path)


def _force_remove(path):
    # Read-only files (common on Windows) cannot be removed until the flag is cleared.
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)


def _prune_empty_dirs(start_dir):
    """
    Best effort: remove start_dir and its parents while they hold nothing but desktop.ini.
    Never removes the sync root or the top-level .tex/.pdf folders.
    """
    root = os.path.abspath('.')
    keep = {root, os.path.join(root, '.tex'), os.path.join(root, '.pdf')}
    current = os.path.abspath(start_dir)
    while current not in keep and current.startswith(root + os.sep) and os.path.isdir(current):
        try:
            entries = os.listdir(current)
            if any(entry.lower() != 'desktop.ini' for entry in entries):
                return
            for entry in entries:
                _force_remove(os.path.join(current, entry))
            # Windows folders with a desktop.ini are often marked read-only, which blocks rmdir.
            os.chmod(current, stat.S_IWRITE)
            os.rmdir(current)
        except OSError as exc:
            click.echo("\t  note: left empty folder %s (%s)" % (os.path.relpath(current, root), exc))
            return
        current = os.path.dirname(current)


def delete_local_file(path):
    if os.path.isfile(path):
        _force_remove(path)
    _prune_empty_dirs(os.path.dirname(path) or '.')

    posix_path = Path(path).as_posix()
    if posix_path.startswith('.tex/') and posix_path.lower().endswith('.tex'):
        pdf_path = '.pdf/' + posix_path[len('.tex/'):-len('.tex')] + '.pdf'
        if os.path.isfile(pdf_path):
            _force_remove(pdf_path)
            click.echo("\t  also removed %s" % pdf_path)
        _prune_empty_dirs(os.path.dirname(pdf_path))


def write_file(path, content):
    _dir = os.path.dirname(path)
    if _dir == path:
        return

    # path is a file
    if _dir != '' and not os.path.exists(_dir):
        os.makedirs(_dir)

    with open(path, 'wb+') as f:
        f.write(content)


def sync_func(files_from, deleted_files, create_file_at_to, delete_file_at_to, create_file_at_from, from_exists_in_to,
              from_equal_to_to, from_newer_than_to, from_name,
              to_name, verbose=False):
    click.echo("\nSyncing files from [%s] to [%s]" % (from_name, to_name))
    click.echo('=' * 40)

    newly_add_list = []
    update_list = []
    delete_list = []
    restore_list = []
    not_restored_list = []
    not_sync_list = []
    synced_list = []

    for name in files_from:
        if from_exists_in_to(name):
            if not from_equal_to_to(name):
                if not from_newer_than_to(name) and not click.confirm(
                        '\n-> Warning: last-edit time stamp of file <%s> from [%s] is older than [%s].\nContinue to '
                        'overwrite with an older version?' % (name, from_name, to_name)):
                    not_sync_list.append(name)
                    continue

                update_list.append(name)
            else:
                synced_list.append(name)
        else:
            newly_add_list.append(name)

    for name in deleted_files:
        delete_choice = click.prompt(
            '\n-> Warning: file <%s> does not exist on [%s] anymore (but it still exists on [%s]).'
            '\nShould the file be [d]eleted, [r]estored or [i]gnored?' % (name, from_name, to_name),
            default="i",
            type=click.Choice(['d', 'r', 'i']))
        if delete_choice == "d":
            delete_list.append(name)
        elif delete_choice == "r":
            restore_list.append(name)
        elif delete_choice == "i":
            not_restored_list.append(name)

    errors = []

    def run_step(header, names, action, verb, side):
        click.echo(header)
        for name in names:
            click.echo("\t%s" % name)
            try:
                action(name)
            except Exception as exc:
                if verbose:
                    print(traceback.format_exc())
                click.echo("\t  [ERROR] could not %s on [%s]: %s" % (verb, side, exc))
                errors.append("%s (%s on [%s])" % (name, verb, side))

    run_step("\n[NEW] Following new file(s) created on [%s]" % to_name,
             newly_add_list, create_file_at_to, "create", to_name)
    run_step("\n[NEW] Following new file(s) created on [%s]" % from_name,
             restore_list, create_file_at_from, "restore", from_name)
    run_step("\n[UPDATE] Following file(s) updated on [%s]" % to_name,
             update_list, create_file_at_to, "update", to_name)
    run_step("\n[DELETE] Following file(s) deleted on [%s]" % to_name,
             delete_list, delete_file_at_to, "delete", to_name)

    click.echo(
        "\n[SYNC] Following file(s) are up to date")
    for name in synced_list:
        click.echo("\t%s" % name)

    click.echo(
        "\n[SKIP] Following file(s) on [%s] have not been synced to [%s]" % (from_name, to_name))
    for name in not_sync_list:
        click.echo("\t%s" % name)

    click.echo(
        "\n[SKIP] Following file(s) on [%s] have not been synced to [%s]" % (to_name, from_name))
    for name in not_restored_list:
        click.echo("\t%s" % name)

    click.echo("")
    if errors:
        click.echo("[ERROR] %d file(s) failed while syncing [%s] to [%s]" % (len(errors), from_name, to_name))
    else:
        click.echo("✅  Synced files from [%s] to [%s]" % (from_name, to_name))
    click.echo("")
    return errors


def execute_action(action, progress_message, success_message, fail_message, verbose_error_logging=False):
    with yaspin(text=progress_message, color="green") as spinner:
        try:
            success = action()
        except:
            if verbose_error_logging:
                print(traceback.format_exc())
            success = False

        if success:
            spinner.write(success_message)
            spinner.ok("✅ ")
        else:
            spinner.fail("💥 ")
            raise click.ClickException(fail_message)

        return success


def load_olignore(olignore_path):
    if not os.path.isfile(olignore_path):
        return []
    with open(olignore_path, 'r', encoding='utf-8') as f:
        return [p.strip() for p in f.read().splitlines() if p.strip() and not p.strip().startswith('#')]


# Always ignored, even if .olignore is missing or gets replaced by a stale copy.
BUILTIN_IGNORES = ['desktop.ini', '*.pyc', '__pycache__', '.olauth', '.olignore']


def is_ignored(name, ignore_patterns):
    """
    gitignore-style matching: a pattern without '/' matches any path segment
    (case-insensitive); a pattern with '/' matches the full relative path.
    """
    posix_name = Path(name).as_posix()
    if posix_name.startswith('./'):
        posix_name = posix_name[2:]
    segments = [s.lower() for s in posix_name.split('/') if s]
    for pattern in BUILTIN_IGNORES + list(ignore_patterns):
        pattern = pattern.strip().replace('\\', '/')
        if pattern.startswith('./'):
            pattern = pattern[2:]
        if not pattern:
            continue
        if '/' in pattern.rstrip('/'):
            if fnmatch.fnmatchcase(posix_name.lower(), pattern.lower()):
                return True
        elif any(fnmatch.fnmatchcase(seg, pattern.rstrip('/').lower()) for seg in segments):
            return True
    return False


def plan_remote_cleanup(project_infos, ignore_patterns):
    """
    Return ('folder', path) / ('file', path) actions that remove every ignored item on Overleaf.
    A folder whose files are all ignored is deleted as a whole instead of file by file.
    """
    def walk(folder, prefix):
        actions = []
        has_files = False
        all_ignored = True
        for key in ('docs', 'fileRefs'):
            for entity in folder.get(key, []):
                path = prefix + entity['name']
                has_files = True
                if is_ignored(path, ignore_patterns):
                    actions.append(('file', path))
                else:
                    all_ignored = False
        for sub in folder.get('folders', []):
            sub_has_files, sub_all_ignored, sub_actions = walk(sub, prefix + sub['name'] + '/')
            has_files = has_files or sub_has_files
            all_ignored = all_ignored and sub_all_ignored
            actions += sub_actions
        if prefix and has_files and all_ignored:
            return has_files, all_ignored, [('folder', prefix.rstrip('/'))]
        return has_files, all_ignored, actions

    return walk(project_infos['rootFolder'][0], '')[2]


def clean_remote_files(overleaf_client, project_id, project_infos, ignore_patterns, verbose=False):
    actions = plan_remote_cleanup(project_infos, ignore_patterns)

    click.echo("\nIgnored item(s) on [remote] to delete from Overleaf")
    click.echo('=' * 40)
    if not actions:
        click.echo("Nothing to clean up.")
        return
    for kind, path in actions:
        click.echo("\t%s%s" % (path, "/  (whole folder)" if kind == 'folder' else ""))

    if not click.confirm("\nDelete these %d item(s) from Overleaf?" % len(actions)):
        click.echo("Cancelled; nothing was deleted.")
        return

    errors = []
    for kind, path in actions:
        try:
            if kind == 'folder':
                overleaf_client.delete_folder(project_id, project_infos, path)
            else:
                overleaf_client.delete_file(project_id, project_infos, path)
        except Exception as exc:
            if verbose:
                print(traceback.format_exc())
            click.echo("\t  [ERROR] could not delete %s: %s" % (path, exc))
            errors.append(path)

    if errors:
        raise click.ClickException(
            "\n[ERROR] %d item(s) could not be deleted from Overleaf:\n\t%s" % (len(errors), "\n\t".join(errors)))
    click.echo("\n✅  Removed %d ignored item(s) from Overleaf" % len(actions))


def is_folder_ignored(folder, ignore_patterns):
    # "name/*" style patterns only match paths inside the folder, so probe a child path too.
    return is_ignored(folder, ignore_patterns) or is_ignored(folder + '/_', ignore_patterns)


def local_folder_list(ignore_patterns):
    folders = []
    for root, dirs, _filenames in os.walk('.'):
        rel_root = Path(root).as_posix()
        rel_root = '' if rel_root == '.' else rel_root[2:] if rel_root.startswith('./') else rel_root
        kept = []
        for d in sorted(dirs):
            path = rel_root + '/' + d if rel_root else d
            if not is_folder_ignored(path, ignore_patterns):
                kept.append(d)
                folders.append(path)
        dirs[:] = kept
    return folders


def remote_folder_set(project_infos):
    found = set()

    def walk(folder, prefix):
        for sub in folder.get('folders', []):
            path = prefix + sub['name']
            found.add(path.lower())
            walk(sub, path + '/')

    walk(project_infos['rootFolder'][0], '')
    return found


def push_empty_folders(overleaf_client, project_id, project_infos, ignore_patterns, verbose=False):
    """Create local folders that have no synced files (and so were not created by uploads) on Overleaf."""
    existing = remote_folder_set(project_infos)
    missing = [f for f in local_folder_list(ignore_patterns) if f.lower() not in existing]

    click.echo("[NEW] Following folder(s) created on [remote]")
    errors = []
    for path in missing:
        click.echo("\t%s/" % path)
        try:
            overleaf_client.ensure_folder(project_id, project_infos, path.split('/'))
        except Exception as exc:
            if verbose:
                print(traceback.format_exc())
            click.echo("\t  [ERROR] could not create folder on [remote]: %s" % exc)
            errors.append("%s/ (create folder on [remote])" % path)
    click.echo("")
    return errors


def olignore_keep_list(olignore_path):
    """
    The list of local files to keep synced, with support for sub-folders.
    """
    # Use os.walk so dot-directories like ".tex" are included.
    # glob.glob('**') intentionally skips names starting with '.'.
    files = []
    for root, _dirs, filenames in os.walk('.'):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    click.echo("="*40)
    if not os.path.isfile(olignore_path):
        click.echo("\nNotice: .olignore file does not exist, will sync all items.")
    else:
        click.echo("\n.olignore: using %s to filter items" % olignore_path)
    ignore_patterns = load_olignore(olignore_path)

    keep_list = [
        Path(item).as_posix()[2:] if Path(item).as_posix().startswith('./') else Path(item).as_posix()
        for item in files
        if not is_ignored(item, ignore_patterns) and not os.path.isdir(item)
    ]
    return keep_list


if __name__ == "__main__":
    main()
