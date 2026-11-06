// The screen an app shows when it finds no game files (front_ios.m, main.m boot_env found no romfs): a split build (win/build_app.py, NXW_SPLIT_DATA) ships the game files
// as a separate "<Game>-data" folder, which the player copies into the app's Documents once. The screen says where it goes, step by step, names the folder the build made
// (NXWDataFolder in Info.plist), shows the size it takes and the space free, and "Check again" looks for it without restarting (the game itself starts on the next launch,
// since the host's environment is set before UIKit starts). "Import ZIP" extracts the data folder zipped on the PC into Documents, with a progress bar. Drawn in the launcher's style: the game card on the left, the steps in an inset-grouped list on the right.
#import <UIKit/UIKit.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#import <BackgroundTasks/BackgroundTasks.h>
#import <UserNotifications/UserNotifications.h>

int nxw_data_found(void);   // main.m: a romfs with the game's marker in Documents, in a folder directly inside it, or in the app

static id info(NSString *k) { return [NSBundle.mainBundle objectForInfoDictionaryKey:k]; }

@interface NxwDataHelpVC : UITableViewController <UIDocumentPickerDelegate>
@property (copy) NSArray<NSArray<NSString *> *> *steps;   // [title, detail]
@property (copy) NSString *status, *importStatus;
@property (strong) UIProgressView *bar;
@property BOOL importing, imported;
@property (copy) NSString *localZip;   // a ZIP the player put into this app's Documents (Files app / Apple Devices): imported without the picker
- (void)refreshImportFooter;
- (void)beginImport:(NSURL *)url scoped:(BOOL)scoped total:(uint64_t)total;
- (void)runImport:(NSURL *)url scoped:(BOOL)scoped total:(uint64_t)total task:(BGTask *)task;
@end

// ---- ZIP import (win/ios/nxw_unzip.c): the data folder zipped on the PC, extracted by the app into its own Documents with a progress bar ----
typedef void (*nxw_unzip_progress)(void *ctx, uint64_t done, uint64_t total, uint64_t files, uint64_t nfiles);
int nxw_unzip(const char *zip, const char *stage, int dry, volatile int *cancel, nxw_unzip_progress cb, void *ctx, uint64_t *total_out, char *err, size_t errn);
static volatile int g_cancel;
static CFAbsoluteTime g_t0, g_last;
static NSProgress *g_task_progress;   // the continued-processing task's progress (its Live Activity), when the import runs as one
static void import_progress(void *ctx, uint64_t done, uint64_t total, uint64_t files, uint64_t nfiles) {
    CFAbsoluteTime now = CFAbsoluteTimeGetCurrent();
    NSProgress *tp = g_task_progress; if (tp) tp.completedUnitCount = (int64_t)(done >> 20);
    if (now - g_last < 0.25 && files < nfiles) return;   // at most four updates a second
    g_last = now;
    NxwDataHelpVC *vc = (__bridge NxwDataHelpVC *)ctx;
    double f = total ? (double)done / (double)total : 0, el = now - g_t0, eta = f > 0.01 ? el / f - el : -1;
    NSString *s = [NSString stringWithFormat:@"Extracting: %@ of %@ · %llu of %llu files%@", [NSByteCountFormatter stringFromByteCount:(long long)done countStyle:NSByteCountFormatterCountStyleFile],
                   [NSByteCountFormatter stringFromByteCount:(long long)total countStyle:NSByteCountFormatterCountStyleFile], (unsigned long long)files, (unsigned long long)nfiles,
                   eta >= 0 ? [NSString stringWithFormat:@" · about %d:%02d left", (int)eta / 60, (int)eta % 60] : @""];
    dispatch_async(dispatch_get_main_queue(), ^{ [vc.bar setProgress:(float)f animated:NO]; vc.importStatus = s; [vc refreshImportFooter]; });
}

@implementation NxwDataHelpVC
- (void)viewDidLoad {
    [super viewDidLoad];
    self.tableView.backgroundColor = UIColor.clearColor;
    self.tableView.rowHeight = UITableViewAutomaticDimension; self.tableView.estimatedRowHeight = 64;
    NSString *doc = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES)[0];
    for (NSString *n in [[NSFileManager.defaultManager contentsOfDirectoryAtPath:doc error:nil] sortedArrayUsingSelector:@selector(compare:)])
        if ([n.pathExtension.lowercaseString isEqualToString:@"zip"]) { self.localZip = [doc stringByAppendingPathComponent:n]; break; }
    if (self.localZip) fprintf(stderr, "import: found %s in Documents\n", self.localZip.lastPathComponent.UTF8String);
    self.importStatus = @"Pick the data ZIP made on the PC, or put it into this app's folder in the Files app (On My iPad › this app) and it is found by itself. The app extracts it into its own Documents.";
}
// Sections: 0 import, 1 the manual steps, 2 check again, 3 free space
- (NSInteger)numberOfSectionsInTableView:(UITableView *)tv { return 4; }
- (NSInteger)tableView:(UITableView *)tv numberOfRowsInSection:(NSInteger)s { return s == 0 ? (self.importing ? 2 : 1) : s == 1 ? (NSInteger)self.steps.count : 1; }
- (NSString *)tableView:(UITableView *)tv titleForHeaderInSection:(NSInteger)s { return s == 0 ? @"Import the data ZIP" : s == 1 ? @"Or copy the folder yourself" : nil; }
- (NSString *)tableView:(UITableView *)tv titleForFooterInSection:(NSInteger)s {
    if (s == 0) return self.importStatus;
    if (s == 1) return @"The folder can keep its name: the app looks in Documents and in every folder directly inside it. Re-signing or reinstalling the app keeps Documents.";
    if (s == 2) return self.status;
    return nil;
}
- (void)refreshImportFooter {
    UITableViewHeaderFooterView *f = [self.tableView footerViewForSection:0];
    if (f) { f.textLabel.text = self.importStatus; [f.textLabel sizeToFit]; [self.tableView beginUpdates]; [self.tableView endUpdates]; }
}
- (UITableViewCell *)tableView:(UITableView *)tv cellForRowAtIndexPath:(NSIndexPath *)ip {
    UITableViewCell *c = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleSubtitle reuseIdentifier:nil];
    c.selectionStyle = UITableViewCellSelectionStyleNone;
    if (ip.section == 0 && ip.row == 1) {   // the progress bar while importing
        UIProgressView *b = [[UIProgressView alloc] initWithProgressViewStyle:UIProgressViewStyleDefault]; b.progressTintColor = UIColor.systemPinkColor;
        b.progress = self.bar ? self.bar.progress : 0; self.bar = b;
        b.translatesAutoresizingMaskIntoConstraints = NO; [c.contentView addSubview:b];
        UILayoutGuide *g = c.contentView.layoutMarginsGuide;
        [NSLayoutConstraint activateConstraints:@[[b.leadingAnchor constraintEqualToAnchor:g.leadingAnchor], [b.trailingAnchor constraintEqualToAnchor:g.trailingAnchor],
            [b.centerYAnchor constraintEqualToAnchor:c.contentView.centerYAnchor], [c.contentView.heightAnchor constraintGreaterThanOrEqualToConstant:44]]];
        return c;
    }
    if (ip.section == 0 || ip.section == 2) {
        UIListContentConfiguration *cfg = [UIListContentConfiguration cellConfiguration];
        cfg.text = ip.section == 2 ? @"Check again" : self.imported ? @"Close the app" : self.importing ? @"Cancel" : self.localZip ? [NSString stringWithFormat:@"Import %@", self.localZip.lastPathComponent] : @"Import ZIP…";
        cfg.textProperties.color = self.importing && ip.section == 0 ? UIColor.systemRedColor : UIColor.systemPinkColor;
        cfg.textProperties.alignment = UIListContentTextAlignmentCenter;
        if (ip.section == 0 && !self.importing && !self.imported) { cfg.image = [UIImage systemImageNamed:@"doc.zipper"]; cfg.imageProperties.tintColor = UIColor.systemPinkColor; }
        c.contentConfiguration = cfg; c.selectionStyle = UITableViewCellSelectionStyleDefault;
    } else if (ip.section == 1) {
        UIListContentConfiguration *cfg = [UIListContentConfiguration subtitleCellConfiguration];
        cfg.text = self.steps[ip.row][0]; cfg.secondaryText = self.steps[ip.row][1];
        cfg.secondaryTextProperties.color = UIColor.secondaryLabelColor; cfg.textToSecondaryTextVerticalPadding = 4;
        cfg.image = [UIImage systemImageNamed:[NSString stringWithFormat:@"%ld.circle.fill", (long)ip.row + 1]];
        cfg.imageProperties.tintColor = UIColor.systemPinkColor;
        c.contentConfiguration = cfg;
    } else {
        UIListContentConfiguration *cfg = [UIListContentConfiguration valueCellConfiguration];
        NSDictionary *a = [NSFileManager.defaultManager attributesOfFileSystemForPath:NSHomeDirectory() error:nil];
        cfg.text = @"Free space on this device";
        cfg.secondaryText = [NSByteCountFormatter stringFromByteCount:[a[NSFileSystemFreeSize] longLongValue] countStyle:NSByteCountFormatterCountStyleFile];
        c.contentConfiguration = cfg;
    }
    return c;
}
- (void)tableView:(UITableView *)tv didSelectRowAtIndexPath:(NSIndexPath *)ip {
    [tv deselectRowAtIndexPath:ip animated:YES];
    if (ip.section == 0 && ip.row == 0) {
        if (self.imported) { fprintf(stderr, "import: closing the app to start the game on the next launch\n"); exit(0); }
        if (self.importing) { g_cancel = 1; self.importStatus = @"Cancelling…"; [self refreshImportFooter]; return; }
        if (self.localZip) { [self documentPicker:nil didPickDocumentsAtURLs:@[[NSURL fileURLWithPath:self.localZip]]]; return; }
        UIDocumentPickerViewController *pk = [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeZIP, UTTypeArchive, UTTypeData, UTTypeItem] asCopy:NO];   // any file can be picked (a ZIP from another app may carry another type, and was greyed out); nxw_unzip checks it
        pk.delegate = self; pk.allowsMultipleSelection = NO;
        UIViewController *top = self.parentViewController ?: self; while (top.presentedViewController) top = top.presentedViewController;
        pk.modalPresentationStyle = UIModalPresentationFormSheet; pk.shouldShowFileExtensions = YES;
        fprintf(stderr, "import: showing the file picker\n");
        [top presentViewController:pk animated:YES completion:nil];
        return;
    }
    if (ip.section != 2) return;
    self.status = nxw_data_found() ? @"Found. Close the app fully (swipe it away in the app switcher) and open it again to play."
                                   : @"Not found yet. A large folder can take several minutes to copy; check that romfs is inside it.";
    [tv reloadSections:[NSIndexSet indexSetWithIndex:2] withRowAnimation:UITableViewRowAnimationNone];
}
- (void)documentPickerWasCancelled:(UIDocumentPickerViewController *)pk { fprintf(stderr, "import: picker cancelled\n"); }
- (void)documentPicker:(UIDocumentPickerViewController *)pk didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
    NSURL *url = urls.firstObject;
    fprintf(stderr, "import: picked %s\n", url ? url.fileSystemRepresentation : "(nothing)");
    if (!url) return;
    BOOL scoped = [url startAccessingSecurityScopedResource];
    self.importStatus = @"Reading the ZIP…"; [self.tableView reloadData];
    NSString *doc = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES)[0];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{   // the central directory of a large ZIP (TotK: 374,588 entries) is read off the main thread
        char err[512] = ""; uint64_t total = 0;
        int rc = nxw_unzip(url.fileSystemRepresentation, [doc stringByAppendingPathComponent:@".nxw_import"].fileSystemRepresentation, 1, NULL, NULL, NULL, &total, err, sizeof err);
        long long fr = [[NSFileManager.defaultManager attributesOfFileSystemForPath:doc error:nil][NSFileSystemFreeSize] longLongValue];
        fprintf(stderr, "import: %s: %s, %.2f GB to extract, %.2f GB free\n", url.lastPathComponent.UTF8String, rc ? err : "readable", total / 1073741824.0, fr / 1073741824.0);
        NSString *why = @(err);
        dispatch_async(dispatch_get_main_queue(), ^{
            if (rc) {
                if (scoped) [url stopAccessingSecurityScopedResource];
                self.importStatus = [NSString stringWithFormat:@"This file cannot be imported: %@", why]; [self.tableView reloadData]; return;
            }
            if ((long long)total + (512ll << 20) > fr) {
                if (scoped) [url stopAccessingSecurityScopedResource];
                self.importStatus = [NSString stringWithFormat:@"Not enough space: the data needs %@, this device has %@ free. Free some space (the ZIP itself can stay until the import ends).",
                                     [NSByteCountFormatter stringFromByteCount:(long long)total countStyle:NSByteCountFormatterCountStyleFile], [NSByteCountFormatter stringFromByteCount:fr countStyle:NSByteCountFormatterCountStyleFile]];
                [self.tableView reloadData]; return;
            }
            [self beginImport:url scoped:scoped total:total];
        });
    });
}
- (void)beginImport:(NSURL *)url scoped:(BOOL)scoped total:(uint64_t)total {
    NSString *doc = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES)[0];
    self.importing = YES; g_cancel = 0; g_t0 = CFAbsoluteTimeGetCurrent(); g_last = 0;
    self.importStatus = @"Starting…"; [self.tableView reloadData];
    UIApplication.sharedApplication.idleTimerDisabled = YES;
    // A notification when it ends (the app may be in the background by then)
    [UNUserNotificationCenter.currentNotificationCenter requestAuthorizationWithOptions:UNAuthorizationOptionAlert | UNAuthorizationOptionSound completionHandler:^(BOOL ok, NSError *e) {}];
    fprintf(stderr, "import: %s (%.2f GB) → %s\n", url.fileSystemRepresentation, total / 1073741824.0, doc.fileSystemRepresentation);
    // iOS / iPadOS 26 and later: a continued-processing task, which keeps running in the background and shows its progress in a Live Activity (the lock screen, the
    // notification area). Its identifier is <bundle ID>.import.<n>, under the <bundle ID>.import.* that Info.plist permits (win/build_app.py). Before 26, or when the system
    // refuses the request, the import runs in the foreground (the screen stays on)
    static BOOL registered; static NxwDataHelpVC *pending; static NSURL *pendingURL; static BOOL pendingScoped; static uint64_t pendingTotal;
    if (@available(iOS 26.0, *)) {
        NSString *base = [NSBundle.mainBundle.bundleIdentifier stringByAppendingString:@".import"];
        NSString *ident = [NSString stringWithFormat:@"%@.%lld", base, (long long)(CFAbsoluteTimeGetCurrent() * 1000)];
        pending = self; pendingURL = url; pendingScoped = scoped; pendingTotal = total;
        if (!registered) registered = [BGTaskScheduler.sharedScheduler registerForTaskWithIdentifier:[base stringByAppendingString:@".*"] usingQueue:nil launchHandler:^(BGTask *task) {
            NxwDataHelpVC *vc = pending; pending = nil;
            if (vc) [vc runImport:pendingURL scoped:pendingScoped total:pendingTotal task:task];
            else [task setTaskCompletedWithSuccess:NO];
        }];
        if (registered) {
            BGContinuedProcessingTaskRequest *rq = [[BGContinuedProcessingTaskRequest alloc] initWithIdentifier:ident title:@"Importing game data"
                subtitle:[NSString stringWithFormat:@"%@ for %@", [NSByteCountFormatter stringFromByteCount:(long long)total countStyle:NSByteCountFormatterCountStyleFile], NSBundle.mainBundle.infoDictionary[@"CFBundleDisplayName"] ?: @"the game"]];
            rq.strategy = BGContinuedProcessingTaskRequestSubmissionStrategyFail;
            [BGTaskScheduler.sharedScheduler submitTaskRequest:rq completionHandler:^(NSError *e) {
                if (!e) { fprintf(stderr, "import: running as a continued-processing task (%s)\n", ident.UTF8String); return; }
                fprintf(stderr, "import: continued-processing task refused (%s); importing in the foreground\n", e.localizedDescription.UTF8String);
                dispatch_async(dispatch_get_main_queue(), ^{ NxwDataHelpVC *vc = pending; pending = nil; if (vc) [vc runImport:url scoped:scoped total:total task:nil]; });
            }];
            return;
        }
    }
    [self runImport:url scoped:scoped total:total task:nil];
}

// The extraction itself, on a background queue; task: the continued-processing task (its progress feeds the Live Activity) or nil
- (void)runImport:(NSURL *)url scoped:(BOOL)scoped total:(uint64_t)total task:(BGTask *)task {
    NSString *doc = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES)[0];
    NSString *stage = [doc stringByAppendingPathComponent:@".nxw_import"];
    __block UIBackgroundTaskIdentifier bg = UIBackgroundTaskInvalid;
    if (task) {
        task.expirationHandler = ^{ g_cancel = 1; };
        if (@available(iOS 26.0, *)) { NSProgress *pr = ((BGContinuedProcessingTask *)task).progress; pr.totalUnitCount = (int64_t)(total >> 20) + 1; g_task_progress = pr; }
    } else bg = [UIApplication.sharedApplication beginBackgroundTaskWithExpirationHandler:^{ g_cancel = 1; }];
    void *ctx = (__bridge void *)self;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        NSFileManager *fm = NSFileManager.defaultManager;
        [fm removeItemAtPath:stage error:nil]; [fm createDirectoryAtPath:stage withIntermediateDirectories:YES attributes:nil error:nil];
        char e2[512] = "";
        int rc = nxw_unzip(url.fileSystemRepresentation, stage.fileSystemRepresentation, 0, &g_cancel, import_progress, ctx, NULL, e2, sizeof e2);
        if (scoped) [url stopAccessingSecurityScopedResource];
        NSString *msg;
        if (!rc) {   // move each top-level item of the staging folder into Documents, replacing an older copy
            for (NSString *n in [fm contentsOfDirectoryAtPath:stage error:nil]) {
                NSString *to = [doc stringByAppendingPathComponent:n];
                [fm removeItemAtPath:to error:nil];
                NSError *me = nil;
                if (![fm moveItemAtPath:[stage stringByAppendingPathComponent:n] toPath:to error:&me]) { rc = -1; snprintf(e2, sizeof e2, "cannot move %s: %s", n.UTF8String, me.localizedDescription.UTF8String); break; }
                [[NSURL fileURLWithPath:to isDirectory:YES] setResourceValue:@YES forKey:NSURLIsExcludedFromBackupKey error:nil];   // game files stay out of device backups
            }
        }
        [fm removeItemAtPath:stage error:nil];
        BOOL ok = !rc && nxw_data_found();
        if (ok && [url.path hasPrefix:doc]) { [fm removeItemAtURL:url error:nil]; fprintf(stderr, "import: removed the imported ZIP from Documents (its space is free again)%c", 10); }
        if (ok) msg = @"Done. Close the app and open it again: the launcher appears, then press Play. The ZIP can be deleted now.";
        else if (!rc) msg = @"Extracted, but the game files were not found in it: the ZIP must hold the data folder (romfs inside).";
        else msg = [NSString stringWithFormat:@"Import stopped: %s. Nothing was left half-written; try again.", e2];
        fprintf(stderr, "import: %s\n", msg.UTF8String);
        g_task_progress = nil;
        if (task) [task setTaskCompletedWithSuccess:ok];
        UNMutableNotificationContent *nc = [UNMutableNotificationContent new];
        nc.title = ok ? @"Game data imported" : @"Game data import stopped";
        nc.body = ok ? @"Open the app to play." : msg; nc.sound = UNNotificationSound.defaultSound;
        [UNUserNotificationCenter.currentNotificationCenter addNotificationRequest:[UNNotificationRequest requestWithIdentifier:@"nxw.import" content:nc trigger:nil] withCompletionHandler:nil];
        dispatch_async(dispatch_get_main_queue(), ^{
            self.importing = NO; self.imported = ok; self.importStatus = msg;
            UIApplication.sharedApplication.idleTimerDisabled = NO;
            if (bg != UIBackgroundTaskInvalid) { [UIApplication.sharedApplication endBackgroundTask:bg]; bg = UIBackgroundTaskInvalid; }
            [self.tableView reloadData];
        });
    });
}
@end

// Shows the screen in the root view controller's view (front_ios.m calls it instead of the plain hint)
void nxw_show_data_help(UIViewController *root) {
    NSString *folder = [info(@"NXWDataFolder") isKindOfClass:NSString.class] ? info(@"NXWDataFolder") : @"the game's data folder";
    NSString *size = [info(@"NXWDataSize") isKindOfClass:NSString.class] ? info(@"NXWDataSize") : nil;
    NSString *name = [info(@"CFBundleDisplayName") isKindOfClass:NSString.class] ? info(@"CFBundleDisplayName") : @"this app";
    NxwDataHelpVC *list = [[NxwDataHelpVC alloc] initWithStyle:UITableViewStyleInsetGrouped];
    list.steps = @[
        @[@"Find the data folder", [NSString stringWithFormat:@"On your PC, next to the IPA: \"%@\"%@ (romfs, msl and aoc inside).", folder, size ? [NSString stringWithFormat:@", %@", size] : @""]],
        @[@"From Windows", [NSString stringWithFormat:@"Apple Devices app (or iTunes) → this device → Files → %@ → drag the whole folder in.", name]],
        @[@"Or on this device", [NSString stringWithFormat:@"Files app → On My %@ → %@ → paste the folder (from a USB drive, a network share or iCloud Drive).", UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad ? @"iPad" : @"iPhone", name]],
        @[@"Restart the app", @"Close the app fully and open it again. The launcher appears, then press Play."],
    ];
    root.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
    root.view.backgroundColor = UIColor.systemGroupedBackgroundColor;

    UIStackView *card = [UIStackView new]; card.axis = UILayoutConstraintAxisVertical; card.alignment = UIStackViewAlignmentCenter; card.spacing = 12;
    UIImage *icon = [UIImage imageNamed:@"AppIcon60x60"];
    if (icon) {
        UIImageView *iv = [[UIImageView alloc] initWithImage:icon]; iv.layer.cornerRadius = 22; iv.layer.cornerCurve = kCACornerCurveContinuous; iv.clipsToBounds = YES;
        [iv.widthAnchor constraintEqualToConstant:96].active = YES; [iv.heightAnchor constraintEqualToConstant:96].active = YES; [card addArrangedSubview:iv];
    }
    UILabel *t = [UILabel new]; t.text = name; t.numberOfLines = 0; t.textAlignment = NSTextAlignmentCenter;
    t.font = [UIFont fontWithDescriptor:[[UIFont preferredFontForTextStyle:UIFontTextStyleTitle1].fontDescriptor fontDescriptorWithSymbolicTraits:UIFontDescriptorTraitBold] size:0];
    [card addArrangedSubview:t];
    UILabel *s = [UILabel new]; s.text = @"Game data needed"; s.textColor = UIColor.systemPinkColor; s.font = [UIFont preferredFontForTextStyle:UIFontTextStyleHeadline]; [card addArrangedSubview:s];
    UILabel *d = [UILabel new]; d.numberOfLines = 0; d.textAlignment = NSTextAlignmentCenter; d.textColor = UIColor.secondaryLabelColor;
    d.font = [UIFont preferredFontForTextStyle:UIFontTextStyleCallout];
    d.text = @"This app was built small: the game files come in a separate folder, copied into the app once.";
    [card addArrangedSubview:d];
    card.translatesAutoresizingMaskIntoConstraints = NO; [root.view addSubview:card];

    [root addChildViewController:list]; list.view.translatesAutoresizingMaskIntoConstraints = NO; [root.view addSubview:list.view]; [list didMoveToParentViewController:root];
    UIView *v = root.view; UILayoutGuide *safe = v.safeAreaLayoutGuide, *left = [UILayoutGuide new]; [v addLayoutGuide:left];
    [NSLayoutConstraint activateConstraints:@[
        [list.view.topAnchor constraintEqualToAnchor:v.topAnchor], [list.view.bottomAnchor constraintEqualToAnchor:v.bottomAnchor],
        [list.view.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor], [list.view.widthAnchor constraintEqualToAnchor:safe.widthAnchor multiplier:0.6],
        [left.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor], [left.trailingAnchor constraintEqualToAnchor:list.view.leadingAnchor],
        [card.centerXAnchor constraintEqualToAnchor:left.centerXAnchor], [card.centerYAnchor constraintEqualToAnchor:v.centerYAnchor],
        [card.widthAnchor constraintLessThanOrEqualToAnchor:left.widthAnchor constant:-32]]];
    fprintf(stderr, "boot: no game files: showing where the data folder (%s) goes\n", folder.UTF8String);
}
